import json
from typing import Dict, Optional, Tuple
import re

# 尝试导入requests，如果失败则使用备用方案
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[WARNING] requests模块不可用，将使用备用方案获取公网IP")


def get_client_ip(request) -> str:
    """获取客户端真实IP地址"""
    # 检查各种代理头
    headers_to_check = [
        'X-Forwarded-For',
        'X-Real-IP',
        'X-Client-IP',
        'X-Forwarded',
        'X-Cluster-Client-IP',
        'Forwarded-For',
        'Forwarded',
        'CF-Connecting-IP',  # Cloudflare
        'True-Client-IP',    # Akamai
    ]
    
    for header in headers_to_check:
        if header in request.headers:
            ip = request.headers[header].split(',')[0].strip()
            if is_valid_ip(ip):
                return ip
    
    # 如果没有代理头，使用远程地址
    return request.client.host


def is_valid_ip(ip: str) -> bool:
    """验证IP地址格式"""
    if not ip:
        return False
    
    # 移除端口号
    ip = ip.split(':')[0]
    
    # IPv4验证
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    if re.match(ipv4_pattern, ip):
        return True
    
    # IPv6验证（简化版）
    ipv6_pattern = r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    if re.match(ipv6_pattern, ip):
        return True
    
    return False


def detect_proxy(request) -> Tuple[bool, Dict]:
    """检测是否使用代理"""
    proxy_indicators = {
        'is_proxy': False,
        'proxy_type': None,
        'proxy_headers': [],
        'real_ip': None,
        'forwarded_ips': []
    }
    
    # 检查代理头
    proxy_headers = [
        'X-Forwarded-For',
        'X-Real-IP',
        'X-Client-IP',
        'X-Forwarded',
        'X-Cluster-Client-IP',
        'Forwarded-For',
        'Forwarded',
        'CF-Connecting-IP',
        'True-Client-IP',
        'Via',
        'Proxy-Connection',
    ]
    
    found_proxy_headers = []
    for header in proxy_headers:
        if header in request.headers:
            found_proxy_headers.append(header)
            proxy_indicators['is_proxy'] = True
    
    proxy_indicators['proxy_headers'] = found_proxy_headers
    
    # 检查X-Forwarded-For链
    if 'X-Forwarded-For' in request.headers:
        forwarded_ips = [ip.strip() for ip in request.headers['X-Forwarded-For'].split(',')]
        proxy_indicators['forwarded_ips'] = forwarded_ips
        if len(forwarded_ips) > 1:
            proxy_indicators['real_ip'] = forwarded_ips[0]
    
    # 检查Via头
    if 'Via' in request.headers:
        proxy_indicators['proxy_type'] = 'HTTP Proxy'
    
    # 检查Cloudflare
    if 'CF-Connecting-IP' in request.headers:
        proxy_indicators['proxy_type'] = 'Cloudflare'
        proxy_indicators['real_ip'] = request.headers['CF-Connecting-IP']
    
    # 检查Akamai
    if 'True-Client-IP' in request.headers:
        proxy_indicators['proxy_type'] = 'Akamai'
        proxy_indicators['real_ip'] = request.headers['True-Client-IP']
    
    return proxy_indicators['is_proxy'], proxy_indicators


def get_public_ip() -> Optional[str]:
    """获取公网IP地址"""
    try:
        if REQUESTS_AVAILABLE:
            # 使用多个服务来获取公网IP
            services = [
                'https://api.ipify.org?format=json',
                'https://httpbin.org/ip',
                'https://api.myip.com',
                'https://ipinfo.io/json',
                'https://api64.ipify.org?format=json',
            ]
            
            for service in services:
                try:
                    print(f"[DEBUG] 尝试从 {service} 获取公网IP...")
                    response = requests.get(service, timeout=5)  # 减少超时时间
                    print(f"[DEBUG] {service} 响应状态: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"[DEBUG] {service} 响应数据: {data}")
                        
                        if 'ip' in data:
                            ip = data['ip']
                            if is_valid_ip(ip) and not is_private_ip(ip):
                                print(f"[DEBUG] 从 {service} 获取到有效公网IP: {ip}")
                                return ip
                        elif 'origin' in data:
                            ip = data['origin']
                            if is_valid_ip(ip) and not is_private_ip(ip):
                                print(f"[DEBUG] 从 {service} 获取到有效公网IP: {ip}")
                                return ip
                        
                except Exception as e:
                    print(f"[DEBUG] {service} 获取失败: {e}")
                    continue
        
        # 如果requests不可用或所有外部服务都失败，尝试使用本地方法
        print("[DEBUG] 使用本地方法获取IP...")
        try:
            import socket
            # 连接到外部服务器来获取本地公网IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(3)  # 设置超时
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"[DEBUG] 本地IP: {local_ip}")
            
            # 如果本地IP不是私有IP，可能是公网IP
            if not is_private_ip(local_ip):
                return local_ip
                
        except Exception as e:
            print(f"[DEBUG] 本地方法失败: {e}")
        
        print("[DEBUG] 所有公网IP获取方法都失败了")
        return None
        
    except Exception as e:
        print(f"[DEBUG] get_public_ip 异常: {e}")
        return None


# 现有IP信息获取实现
def get_ip_info(ip: str) -> Optional[Dict]:
    """获取IP地址信息（地理位置、ISP等）"""
    if not REQUESTS_AVAILABLE:
        return None
        
    try:
        # 使用ip-api.com的免费服务
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'country': data.get('country'),
                    'region': data.get('regionName'),
                    'city': data.get('city'),
                    'isp': data.get('isp'),  # 可以获取ISP信息
                    'org': data.get('org'),  # 可以获取组织机构信息
                    'timezone': data.get('timezone'),
                    'lat': data.get('lat'),
                    'lon': data.get('lon'),
                }
    except Exception:
        pass
    
    return None


def is_private_ip(ip: str) -> bool:
    """检查是否为私有IP地址"""
    if not is_valid_ip(ip):
        return False
    
    # 私有IP地址范围
    private_ranges = [
        ('10.0.0.0', '10.255.255.255'),
        ('172.16.0.0', '172.31.255.255'),
        ('192.168.0.0', '192.168.255.255'),
        ('127.0.0.0', '127.255.255.255'),
        ('169.254.0.0', '169.254.255.255'),  # Link-local
    ]
    
    ip_parts = [int(x) for x in ip.split('.')]
    ip_num = ip_parts[0] << 24 | ip_parts[1] << 16 | ip_parts[2] << 8 | ip_parts[3]
    
    for start_ip, end_ip in private_ranges:
        start_parts = [int(x) for x in start_ip.split('.')]
        end_parts = [int(x) for x in end_ip.split('.')]
        
        start_num = start_parts[0] << 24 | start_parts[1] << 16 | start_parts[2] << 8 | start_parts[3]
        end_num = end_parts[0] << 24 | end_parts[1] << 16 | end_parts[2] << 8 | end_parts[3]
        
        if start_num <= ip_num <= end_num:
            return True
    
    return False
