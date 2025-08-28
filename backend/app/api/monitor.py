from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import psutil
import subprocess
from typing import Dict, Any, List
from collections import defaultdict
import docker
from docker.errors import DockerException

from app.db.database import get_db
from app.schemas.common import ResponseModel
from app.utils.geo_utils import get_ip_location_simple, get_ip_location_summary

router = APIRouter()

@router.get("/system", response_model=ResponseModel)
def get_system_info():
    """获取系统信息"""
    try:
        # CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # 内存信息
        memory = psutil.virtual_memory()
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        
        # 网络信息
        network = psutil.net_io_counters()
        
        # 获取网络连接数
        try:
            connections = psutil.net_connections()
            network_connections = len(connections)
        except (psutil.AccessDenied, psutil.ZombieProcess):
            network_connections = 0
        
        # 系统负载信息
        try:
            load_avg = psutil.getloadavg()
            load_info = {
                "load_1min": round(load_avg[0], 2),
                "load_5min": round(load_avg[1], 2),
                "load_15min": round(load_avg[2], 2),
                "load_per_cpu": round(load_avg[0] / cpu_count, 2) if cpu_count > 0 else 0
            }
        except Exception:
            load_info = {
                "load_1min": 0,
                "load_5min": 0,
                "load_15min": 0,
                "load_per_cpu": 0
            }
        
        # 磁盘分区信息
        try:
            disk_partitions = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_partitions.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0
                    })
                except (PermissionError, FileNotFoundError):
                    # 跳过无法访问的分区
                    continue
        except Exception:
            disk_partitions = []
        
        return ResponseModel(
            code=0,
            message="获取系统信息成功",
            data={
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                    "connections": network_connections
                },
                "load": load_info,
                "disk_partitions": disk_partitions
            }
        )
    except Exception as e:
        return ResponseModel(
            code=5000,
            message=f"获取系统信息失败: {str(e)}"
        )

@router.get("/network", response_model=ResponseModel)
def get_network_info():
    """获取网络连接信息"""
    try:
        # 获取网络连接
        connections = psutil.net_connections()
        
        # 统计TCP/UDP连接
        tcp_connections = [conn for conn in connections if conn.status == 'ESTABLISHED' and conn.type == 1]
        udp_connections = [conn for conn in connections if conn.type == 2]
        
        # 获取网络接口信息
        interfaces = psutil.net_if_addrs()
        
        return ResponseModel(
            code=0,
            message="获取网络信息成功",
            data={
                "connections": {
                    "total": len(connections),
                    "tcp_established": len(tcp_connections),
                    "udp": len(udp_connections)
                },
                "interfaces": {
                    name: {
                        "addresses": [addr.address for addr in addrs if addr.family == 2]  # IPv4
                    } for name, addrs in interfaces.items()
                }
            }
        )
    except Exception as e:
        return ResponseModel(
            code=5000,
            message=f"获取网络信息失败: {str(e)}"
        )

@router.get("/processes", response_model=ResponseModel)
def get_process_info():
    """获取进程信息"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 按CPU使用率排序，取前10个
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        top_cpu_processes = processes[:10]
        
        # 按内存使用率排序，取前10个
        processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        top_memory_processes = processes[:10]
        
        return ResponseModel(
            code=0,
            message="获取进程信息成功",
            data={
                "total_processes": len(processes),
                "top_cpu_processes": top_cpu_processes,
                "top_memory_processes": top_memory_processes
            }
        )
    except Exception as e:
        return ResponseModel(
            code=5000,
            message=f"获取进程信息失败: {str(e)}"
        )

@router.get("/containers", response_model=ResponseModel)
def get_container_info():
    """获取Docker容器信息 (使用 Docker SDK - 优化版)"""
    containers_data = []
    debug_info = []

    try:
        client = docker.from_env()
        client.ping()
        debug_info.append("成功连接到 Docker daemon")
        
        # 获取所有容器（包括已停止的，以便未来扩展）
        # 如果只需要运行中的，继续使用 client.containers.list()
        all_containers = client.containers.list(all=True)
        debug_info.append(f"找到 {len(all_containers)} 个容器 (包括已停止的)")

        for container in all_containers:
            try:
                # container.attrs 包含了 inspect() 的所有信息，通常无需额外API调用
                container_attrs = container.attrs
                
                # --- 1. 重新格式化端口映射信息 (更健壮) ---
                ports_info = []
                # NetworkSettings.Ports 是 inspect API 中的标准字段
                port_bindings = container_attrs.get('NetworkSettings', {}).get('Ports', {})
                for container_port, host_bindings in port_bindings.items():
                    if host_bindings:
                        for binding in host_bindings:
                            host_ip = binding.get('HostIp', '0.0.0.0')
                            host_port = binding.get('HostPort', '')
                            ports_info.append(f"{host_ip}:{host_port}->{container_port}")
                ports_str = ", ".join(ports_info) if ports_info else "无端口映射"

                # --- 2. 从 .attrs 中获取并格式化挂载信息 (更高效) ---
                mounts_info = []
                mounts_data = container_attrs.get('Mounts', [])
                for mount in mounts_data:
                    source = mount.get('Source', 'N/A')
                    destination = mount.get('Destination', 'N/A')
                    mode = 'ro' if mount.get('RW', True) is False else 'rw'
                    mount_type = mount.get('Type', 'bind')
                    # 格式化为 docker-compose 风格的字符串
                    mounts_info.append(f"{source}:{destination}:{mode} ({mount_type})")
                
                # --- 仅当容器运行时才获取实时统计信息 ---
                if container.status == 'running':
                    try:
                        stats = container.stats(stream=False)
                        
                        # CPU 计算
                        cpu_percent = 0.0
                        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                        system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                        online_cpus = stats['cpu_stats'].get('online_cpus', len(stats['cpu_stats']['cpu_usage']['percpu_usage'] or []))
                        
                        if system_cpu_delta > 0.0 and cpu_delta > 0.0:
                            cpu_percent = (cpu_delta / system_cpu_delta) * online_cpus * 100.0

                        # 内存计算
                        mem_usage = "0B"
                        mem_limit = "0B"
                        mem_percent = "0.00%"
                        
                        if 'usage' in stats['memory_stats']:
                            mem_usage_bytes = stats['memory_stats']['usage']
                            mem_limit_bytes = stats['memory_stats']['limit']
                            mem_usage = f"{mem_usage_bytes / (1024*1024):.2f}MiB"
                            mem_limit = f"{mem_limit_bytes / (1024*1024):.2f}MiB"
                            mem_percent = f"{(mem_usage_bytes / mem_limit_bytes) * 100:.2f}%" if mem_limit_bytes > 0 else "0.00%"

                        # 网络和磁盘IO
                        net_rx, net_tx = 0, 0
                        for if_name, data in stats.get('networks', {}).items():
                            net_rx += data['rx_bytes']
                            net_tx += data['tx_bytes']
                        network_io = f"{net_rx / (1024*1024):.2f}MiB / {net_tx / (1024*1024):.2f}MiB"
                        
                        block_read = stats['blkio_stats']['io_service_bytes_recursive'][0]['value'] if stats['blkio_stats']['io_service_bytes_recursive'] else 0
                        block_write = stats['blkio_stats']['io_service_bytes_recursive'][1]['value'] if len(stats['blkio_stats']['io_service_bytes_recursive']) > 1 else 0
                        block_io = f"{block_read / (1024*1024):.2f}MiB / {block_write / (1024*1024):.2f}MiB"
                        
                        debug_info.append(f"成功获取容器 {container.name} 的统计信息")
                        
                    except (KeyError, IndexError, TypeError) as e:
                        debug_info.append(f"处理容器 {container.name} 的统计信息时出错: {e} - 将使用默认值")
                        # 如果解析stats失败，使用默认值
                        cpu_percent = 0.0
                        mem_usage = "N/A"
                        mem_limit = "N/A"
                        mem_percent = "0.00%"
                        network_io = "N/A"
                        block_io = "N/A"
                else:
                    # 对于已停止的容器，提供默认值
                    cpu_percent = 0.0
                    mem_usage = "N/A"
                    mem_limit = "N/A"
                    mem_percent = "0.00%"
                    network_io = "N/A"
                    block_io = "N/A"

                containers_data.append({
                    "name": container.name,
                    "id": container.short_id,  # 增加容器ID，非常有用
                    "image": ", ".join(container.image.tags) if container.image.tags else container.image.short_id,
                    "status": container.status,
                    "created": container_attrs.get('Created', ''),  # 增加创建时间
                    "ports": ports_str,
                    "mounts": mounts_info,  # 使用格式化后的挂载信息
                    "cpu_percent": f"{cpu_percent:.2f}" if isinstance(cpu_percent, float) else str(cpu_percent),
                    "memory_usage": f"{mem_usage} / {mem_limit}",
                    "memory_percent": mem_percent.replace('%', ''),
                    "network_io": network_io,
                    "block_io": block_io
                })
                debug_info.append(f"成功处理容器 {container.name}")
            
            except Exception as e:
                debug_info.append(f"处理容器 {container.name} 时出错: {e} - 将使用基本信息")
                # 提供最基本的容器信息
                containers_data.append({
                    "name": container.name,
                    "id": getattr(container, 'short_id', 'N/A'),
                    "image": getattr(container.image, 'short_id', 'N/A'),
                    "status": getattr(container, 'status', 'unknown'),
                    "created": "N/A",
                    "ports": "获取失败",
                    "mounts": [],
                    "cpu_percent": "0.00",
                    "memory_usage": "N/A",
                    "memory_percent": "0",
                    "network_io": "N/A",
                    "block_io": "N/A"
                })

        return ResponseModel(
            code=0,
            message="获取容器信息成功",
            data={
                "containers": containers_data,
                "total_containers": len(containers_data),
                "debug_info": debug_info
            }
        )

    except DockerException as e:
        # 捕获所有Docker相关的错误，例如连接被拒绝
        message = "无法连接到Docker守护进程。请检查服务是否运行以及用户权限。"
        debug_info.append(f"Docker SDK 错误: {e}")
        return ResponseModel(
            code=5003, 
            message=message, 
            data={
                "containers": [], 
                "total_containers": 0, 
                "debug_info": debug_info
            }
        )
    except Exception as e:
        debug_info.append(f"未知异常: {str(e)}")
        return ResponseModel(
            code=5000, 
            message=f"获取容器信息失败: {str(e)}", 
            data={
                "containers": [], 
                "total_containers": 0, 
                "debug_info": debug_info
            }
        )

@router.get("/firewall-status", response_model=ResponseModel)
def get_firewall_status():
    """获取防火墙状态信息"""
    try:
        # 检查nftables服务状态
        result = subprocess.run(['systemctl', 'is-active', 'nftables'], 
                              capture_output=True, text=True)
        nftables_status = result.stdout.strip()
        
        # 获取nftables规则数量
        result = subprocess.run(['nft', 'list', 'ruleset'], 
                              capture_output=True, text=True)
        rules_count = len(result.stdout.split('\n')) if result.returncode == 0 else 0
        
        return ResponseModel(
            code=0,
            message="获取防火墙状态成功",
            data={
                "nftables_status": nftables_status,
                "rules_count": rules_count,
                "is_running": nftables_status == "active"
            }
        )
    except Exception as e:
        return ResponseModel(
            code=5000,
            message=f"获取防火墙状态失败: {str(e)}"
        )

@router.get("/connections", response_model=ResponseModel)
def get_network_connections():
    """获取详细的网络连接信息，包含IP地理位置"""
    try:
        # 获取网络连接
        connections = psutil.net_connections()
        
        # 统计连接信息
        connection_stats = {
            'total': len(connections),
            'tcp_established': 0,
            'tcp_listen': 0,
            'tcp_time_wait': 0,
            'udp': 0,
            'other': 0
        }
        
        # 按IP地址分组统计
        ip_connections = defaultdict(list)
        connection_details = []
        
        for conn in connections:
            # 统计连接状态
            if conn.type == 1:  # TCP
                if conn.status == 'ESTABLISHED':
                    connection_stats['tcp_established'] += 1
                elif conn.status == 'LISTEN':
                    connection_stats['tcp_listen'] += 1
                elif conn.status == 'TIME_WAIT':
                    connection_stats['tcp_time_wait'] += 1
                else:
                    connection_stats['other'] += 1
            elif conn.type == 2:  # UDP
                connection_stats['udp'] += 1
            else:
                connection_stats['other'] += 1
            
            # 收集远程IP地址
            if conn.raddr and conn.raddr.ip:
                remote_ip = conn.raddr.ip
                ip_connections[remote_ip].append({
                    'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A",
                    'remote_address': f"{remote_ip}:{conn.raddr.port}",
                    'status': conn.status,
                    'type': 'TCP' if conn.type == 1 else 'UDP' if conn.type == 2 else 'Other',
                    'pid': conn.pid
                })
        
        # 获取IP地理位置信息
        ip_locations = {}
        for ip in ip_connections.keys():
            # 跳过本地IP和私有IP
            if ip in ['127.0.0.1', 'localhost', '::1'] or ip.startswith(('192.168.', '10.', '172.')):
                ip_locations[ip] = {
                    'ip': ip,
                    'country': '本地',
                    'city': '本地网络',
                    'region': '本地',
                    'timezone': '本地',
                    'summary': f"{ip} (本地网络)"
                }
            else:
                # 获取地理位置信息
                geo_info = get_ip_location_simple(ip)
                if geo_info:
                    ip_locations[ip] = geo_info
                    ip_locations[ip]['summary'] = get_ip_location_summary(ip)
                else:
                    ip_locations[ip] = {
                        'ip': ip,
                        'country': '未知',
                        'city': '未知',
                        'region': '未知',
                        'timezone': '未知',
                        'summary': f"{ip} (位置未知)"
                    }
        
        # 构建连接详情列表
        for ip, connections_list in ip_connections.items():
            connection_details.append({
                'ip': ip,
                'location': ip_locations.get(ip, {}),
                'connection_count': len(connections_list),
                'connections': connections_list
            })
        
        # 按连接数量排序
        connection_details.sort(key=lambda x: x['connection_count'], reverse=True)
        
        return ResponseModel(
            code=0,
            message="获取网络连接信息成功",
            data={
                'stats': connection_stats,
                'connections': connection_details,
                'total_unique_ips': len(ip_connections)
            }
        )
    except Exception as e:
        return ResponseModel(
            code=5000,
            message=f"获取网络连接信息失败: {str(e)}"
        )

@router.get("/connections/{ip}", response_model=ResponseModel)
def get_ip_connection_details(ip: str):
    """获取特定IP地址的连接详情"""
    try:
        # 获取网络连接
        connections = psutil.net_connections()
        
        # 筛选指定IP的连接
        ip_connections = []
        for conn in connections:
            if conn.raddr and conn.raddr.ip == ip:
                ip_connections.append({
                    'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A",
                    'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}",
                    'status': conn.status,
                    'type': 'TCP' if conn.type == 1 else 'UDP' if conn.type == 2 else 'Other',
                    'pid': conn.pid
                })
        
        # 获取地理位置信息
        geo_info = get_ip_location_simple(ip)
        if not geo_info:
            geo_info = {
                'ip': ip,
                'country': '未知',
                'city': '未知',
                'region': '未知',
                'timezone': '未知'
            }
        
        return ResponseModel(
            code=0,
            message="获取IP连接详情成功",
            data={
                'ip': ip,
                'location': geo_info,
                'connection_count': len(ip_connections),
                'connections': ip_connections
            }
        )
    except Exception as e:
        return ResponseModel(
            code=5000,
            message=f"获取IP连接详情失败: {str(e)}"
        )
