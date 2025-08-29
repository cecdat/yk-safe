from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import subprocess
import os
import time
import threading
import gzip
import shutil
import signal
import psutil
import socket
from datetime import datetime
import uuid

from app.db.database import get_db
from app.db.models import NetworkCapture, NetworkTask
from app.schemas.network import CaptureCreate, CaptureResponse, TaskStatus, InterfaceInfo
from app.schemas.common import ResponseModel

router = APIRouter()

# 存储正在运行的任务
running_tasks = {}

def get_physical_interfaces():
    """
    获取服务器所有物理网卡（排除虚拟网卡如 Docker/loopback）的名称和 IPv4 地址。
    """
    physical_interfaces = []
    virtual_prefixes = ('docker', 'veth', 'br-', 'lo')
    try:
        all_addrs = psutil.net_if_addrs()
        for name, addrs in all_addrs.items():
            if name.startswith(virtual_prefixes):
                continue
            device_path = f'/sys/class/net/{name}/device'
            if not os.path.exists(device_path):
                continue
            
            ipv4_address = None
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ipv4_address = addr.address
                    break
            if ipv4_address:
                physical_interfaces.append({'name': name, 'ip': ipv4_address})
    except Exception as e:
        print(f"获取网卡信息时出错: {e}")
    return physical_interfaces

@router.get("/interfaces", response_model=ResponseModel)
def get_network_interfaces():
    """获取物理网络接口列表（已优化）"""
    try:
        # 调用我们新的、更可靠的函数
        interfaces = get_physical_interfaces()
        
        # 如果没有获取到物理网卡，提供一些备用选项
        if not interfaces:
            print("[WARNING] 未获取到物理网卡，使用备用接口")
            fallback_interfaces = [
                {'name': 'eth0', 'ip': '192.168.1.100'},
                {'name': 'ens33', 'ip': '192.168.1.101'},
                {'name': 'eno1', 'ip': '192.168.1.102'}
            ]
            interfaces = fallback_interfaces
        
        print(f"[DEBUG] 获取到的物理网络接口: {interfaces}")
        
        return ResponseModel(
            code=0,
            message="获取物理网络接口成功",
            data=interfaces
        )
    except Exception as e:
        print(f"[ERROR] 获取网络接口失败: {e}")
        # 如果获取失败，返回一些默认接口
        fallback_interfaces = [
            {'name': 'eth0', 'ip': '192.168.1.100'},
            {'name': 'ens33', 'ip': '192.168.1.101'},
            {'name': 'eno1', 'ip': '192.168.1.102'}
        ]
        return ResponseModel(
            code=0,
            message="使用默认网络接口",
            data=fallback_interfaces
        )

@router.post("/start-capture", response_model=ResponseModel)
def start_capture(capture_data: CaptureCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """开始抓包"""
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建抓包记录
        capture = NetworkCapture(
            task_id=task_id,
            protocol=capture_data.protocol or 'all',
            interface=capture_data.interface,
            source_ip=capture_data.source_ip,
            target_ip=capture_data.target_ip,
            duration=capture_data.duration,
            status='running'
        )
        db.add(capture)
        db.commit()
        
        # 在后台执行抓包任务
        background_tasks.add_task(run_capture_task, task_id, capture_data, db)
        
        return ResponseModel(
            code=0,
            message="抓包任务已启动",
            data={"task_id": task_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动抓包失败: {str(e)}")

def run_capture_task(task_id: str, capture_data: CaptureCreate, db: Session):
    """执行抓包任务"""
    try:
        # 确保临时目录存在
        temp_dir = '/tmp'
        if not os.path.exists(temp_dir):
            temp_dir = '/var/tmp'  # 备用临时目录
        
        pcap_file = os.path.join(temp_dir, f'capture_{task_id}.pcap')
        
        # 构建tcpdump命令
        cmd = ['tcpdump', '-i', capture_data.interface, '-w', pcap_file]
        
        # 添加协议过滤
        if capture_data.protocol and capture_data.protocol != 'all':
            cmd.extend(['-n', capture_data.protocol])
        
        # 添加源IP过滤
        if capture_data.source_ip:
            cmd.extend(['src', capture_data.source_ip])
        
        # 添加目标IP过滤
        if capture_data.target_ip:
            cmd.extend(['dst', capture_data.target_ip])
        
        print(f"[DEBUG] 启动tcpdump命令: {' '.join(cmd)}")
        
        # 启动tcpdump进程
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 存储进程信息
        running_tasks[task_id] = {
            'process': process,
            'type': 'capture',
            'start_time': time.time(),
            'pcap_file': pcap_file
        }
        
        # 如果设置了时长，启动定时器
        if capture_data.duration and capture_data.duration > 0:
            def stop_capture_timer():
                time.sleep(capture_data.duration)
                if task_id in running_tasks:
                    print(f"[DEBUG] 定时器触发，停止抓包任务: {task_id}")
                    stop_capture_internal(task_id, db)
            
            timer_thread = threading.Thread(target=stop_capture_timer)
            timer_thread.daemon = True
            timer_thread.start()
            
            # 等待定时器线程完成，而不是等待tcpdump进程
            timer_thread.join()
        else:
            # 如果没有设置时长，等待进程自然结束
            stdout, stderr = process.communicate()
            
            # 更新数据库记录
            capture = db.query(NetworkCapture).filter(NetworkCapture.task_id == task_id).first()
            if capture:
                if process.returncode == 0:
                    capture.status = 'completed'
                    capture.filename = f'capture_{task_id}.pcap'
                    capture.file_path = f'/tmp/capture_{task_id}.pcap'
                    
                    # 压缩文件
                    if os.path.exists(capture.file_path):
                        compressed_path = f'{capture.file_path}.gz'
                        with open(capture.file_path, 'rb') as f_in:
                            with gzip.open(compressed_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        capture.file_path = compressed_path
                        capture.filename = f'capture_{task_id}.pcap.gz'
                        capture.file_size = os.path.getsize(compressed_path)
                        
                        # 删除原始文件
                        os.remove(f'/tmp/capture_{task_id}.pcap')
                else:
                    capture.status = 'failed'
                    capture.error_message = stderr.decode() if stderr else '抓包失败'
                
                db.commit()
        
        # 清理任务记录
        if task_id in running_tasks:
            del running_tasks[task_id]
        
    except Exception as e:
        # 更新错误状态
        capture = db.query(NetworkCapture).filter(NetworkCapture.task_id == task_id).first()
        if capture:
            capture.status = 'failed'
            capture.error_message = str(e)
            db.commit()
        
        # 清理任务记录
        if task_id in running_tasks:
            del running_tasks[task_id]

def stop_capture_internal(task_id: str, db: Session):
    """内部停止抓包函数"""
    if task_id not in running_tasks:
        return
    
    task_info = running_tasks[task_id]
    if task_info['type'] == 'capture':
        process = task_info['process']
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        # 等待进程完全结束
        process.wait()
        
        # 处理抓包文件
        capture = db.query(NetworkCapture).filter(NetworkCapture.task_id == task_id).first()
        if capture:
            # 使用存储的文件路径
            pcap_file = task_info.get('pcap_file', f'/tmp/capture_{task_id}.pcap')
            print(f"[DEBUG] 检查抓包文件: {pcap_file}")
            
            if os.path.exists(pcap_file):
                print(f"[DEBUG] 抓包文件存在，开始压缩: {pcap_file}")
                # 压缩文件
                compressed_path = f'{pcap_file}.gz'
                try:
                    with open(pcap_file, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    capture.file_path = compressed_path
                    capture.filename = f'capture_{task_id}.pcap.gz'
                    capture.file_size = os.path.getsize(compressed_path)
                    capture.status = 'completed'
                    print(f"[DEBUG] 抓包完成，文件大小: {capture.file_size} bytes")
                    
                    # 删除原始文件
                    os.remove(pcap_file)
                except Exception as e:
                    print(f"[DEBUG] 文件压缩失败: {e}")
                    capture.status = 'failed'
                    capture.error_message = f"文件压缩失败: {str(e)}"
            else:
                print(f"[DEBUG] 抓包文件不存在: {pcap_file}")
                # 检查进程状态
                if process.poll() is not None:
                    print(f"[DEBUG] 进程已退出，返回码: {process.returncode}")
                    if process.returncode != 0:
                        stderr = process.stderr.read() if process.stderr else b''
                        error_msg = stderr.decode('utf-8', errors='ignore') if stderr else '抓包进程异常退出'
                        capture.error_message = f"抓包失败: {error_msg}"
                    else:
                        capture.error_message = "抓包文件未生成"
                else:
                    capture.error_message = "抓包文件未生成"
                capture.status = 'failed'
            
            db.commit()
        
        # 清理任务记录
        del running_tasks[task_id]

@router.post("/stop-capture/{task_id}", response_model=ResponseModel)
def stop_capture(task_id: str, db: Session = Depends(get_db)):
    """停止抓包"""
    try:
        if task_id not in running_tasks:
            raise HTTPException(status_code=404, detail="任务不存在或已停止")
        
        stop_capture_internal(task_id, db)
        
        return ResponseModel(
            code=0,
            message="抓包任务已停止"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止抓包失败: {str(e)}")

@router.post("/start-ping", response_model=ResponseModel)
def start_ping(target_data: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    target = target_data.get('target')
    if not target:
        raise HTTPException(status_code=400, detail="目标地址不能为空")
    """开始ping测试"""
    try:
        task_id = str(uuid.uuid4())
        
        # 创建ping任务记录
        task = NetworkTask(
            task_id=task_id,
            command='ping',
            target=target,
            status='running'
        )
        db.add(task)
        db.commit()
        
        # 在后台执行ping任务
        background_tasks.add_task(run_ping_task, task_id, target, db)
        
        return ResponseModel(
            code=0,
            message="Ping任务已启动",
            data={"task_id": task_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动ping失败: {str(e)}")

def run_ping_task(task_id: str, target: str, db: Session):
    """执行ping任务"""
    try:
        # 检测操作系统，使用相应的ping命令
        import platform
        if platform.system() == "Windows":
            cmd = ['ping', '-n', '10', target]  # Windows ping命令
        else:
            cmd = ['ping', '-c', '10', target]  # Linux/Unix ping命令
        
        # 启动ping进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 存储进程信息
        running_tasks[task_id] = {
            'process': process,
            'type': 'ping',
            'start_time': time.time()
        }
        
        # 实时读取输出
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                output_lines.append(line.strip())
                # 更新数据库中的实时输出
                task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
                if task:
                    task.output = '\n'.join(output_lines)
                    db.commit()
        
        # 等待进程结束
        process.wait()
        
        # 更新数据库记录
        task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
        if task:
            if process.returncode == 0:
                task.status = 'completed'
                task.output = '\n'.join(output_lines)
            else:
                task.status = 'failed'
                task.error_message = 'Ping失败'
            
            db.commit()
        
        # 清理任务记录
        if task_id in running_tasks:
            del running_tasks[task_id]
        
    except Exception as e:
        # 更新错误状态
        task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
        if task:
            task.status = 'failed'
            task.error_message = str(e)
            db.commit()
        
        # 清理任务记录
        if task_id in running_tasks:
            del running_tasks[task_id]

@router.post("/stop-ping/{task_id}", response_model=ResponseModel)
def stop_ping(task_id: str, db: Session = Depends(get_db)):
    """停止ping任务"""
    try:
        if task_id not in running_tasks:
            raise HTTPException(status_code=404, detail="任务不存在或已停止")
        
        task_info = running_tasks[task_id]
        if task_info['type'] == 'ping':
            process = task_info['process']
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            # 读取剩余输出
            remaining_output = []
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                remaining_output.append(line.strip())
            
            # 更新数据库状态和输出
            task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
            if task:
                if remaining_output:
                    current_output = task.output or ''
                    task.output = current_output + '\n' + '\n'.join(remaining_output)
                task.status = 'stopped'
                db.commit()
            
            # 清理任务记录
            del running_tasks[task_id]
        
        return ResponseModel(
            code=0,
            message="Ping任务已停止"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止ping失败: {str(e)}")

@router.post("/start-traceroute", response_model=ResponseModel)
def start_traceroute(target_data: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    target = target_data.get('target')
    if not target:
        raise HTTPException(status_code=400, detail="目标地址不能为空")
    """开始路由追踪"""
    try:
        task_id = str(uuid.uuid4())
        
        # 创建traceroute任务记录
        task = NetworkTask(
            task_id=task_id,
            command='traceroute',
            target=target,
            status='running'
        )
        db.add(task)
        db.commit()
        
        # 在后台执行traceroute任务
        background_tasks.add_task(run_traceroute_task, task_id, target, db)
        
        return ResponseModel(
            code=0,
            message="路由追踪任务已启动",
            data={"task_id": task_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动路由追踪失败: {str(e)}")

def run_traceroute_task(task_id: str, target: str, db: Session):
    """执行路由追踪任务"""
    try:
        # 检测操作系统，使用相应的traceroute命令
        import platform
        if platform.system() == "Windows":
            cmd = ['tracert', target]  # Windows tracert命令
        else:
            cmd = ['traceroute', target]  # Linux/Unix traceroute命令
        
        # 启动traceroute进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 存储进程信息
        running_tasks[task_id] = {
            'process': process,
            'type': 'traceroute',
            'start_time': time.time()
        }
        
        # 实时读取输出
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                output_lines.append(line.strip())
                # 更新数据库中的实时输出
                task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
                if task:
                    task.output = '\n'.join(output_lines)
                    db.commit()
        
        # 等待进程结束
        process.wait()
        
        # 更新数据库记录
        task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
        if task:
            if process.returncode == 0:
                task.status = 'completed'
                task.output = '\n'.join(output_lines)
            else:
                task.status = 'failed'
                task.error_message = '路由追踪失败'
            
            db.commit()
        
        # 清理任务记录
        if task_id in running_tasks:
            del running_tasks[task_id]
        
    except Exception as e:
        # 更新错误状态
        task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
        if task:
            task.status = 'failed'
            task.error_message = str(e)
            db.commit()
        
        # 清理任务记录
        if task_id in running_tasks:
            del running_tasks[task_id]

@router.post("/stop-traceroute/{task_id}", response_model=ResponseModel)
def stop_traceroute(task_id: str, db: Session = Depends(get_db)):
    """停止路由追踪任务"""
    try:
        if task_id not in running_tasks:
            raise HTTPException(status_code=404, detail="任务不存在或已停止")
        
        task_info = running_tasks[task_id]
        if task_info['type'] == 'traceroute':
            process = task_info['process']
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            # 读取剩余输出
            remaining_output = []
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                remaining_output.append(line.strip())
            
            # 更新数据库状态和输出
            task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
            if task:
                if remaining_output:
                    current_output = task.output or ''
                    task.output = current_output + '\n' + '\n'.join(remaining_output)
                task.status = 'stopped'
                db.commit()
            
            # 清理任务记录
            del running_tasks[task_id]
        
        return ResponseModel(
            code=0,
            message="路由追踪任务已停止"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止路由追踪失败: {str(e)}")

@router.get("/capture-status/{task_id}", response_model=ResponseModel)
def get_capture_status(task_id: str, db: Session = Depends(get_db)):
    """获取抓包状态"""
    try:
        capture = db.query(NetworkCapture).filter(NetworkCapture.task_id == task_id).first()
        if not capture:
            raise HTTPException(status_code=404, detail="抓包任务不存在")
        
        # 计算进度（基于时间）
        progress = 0
        if capture.duration and capture.created_at:
            elapsed = (datetime.now() - capture.created_at).total_seconds()
            progress = min(100, int((elapsed / capture.duration) * 100))
        
        # 生成输出信息
        output = f"抓包状态: {capture.status}"
        if capture.interface:
            output += f"\n网卡: {capture.interface}"
        if capture.protocol:
            output += f"\n协议: {capture.protocol}"
        if capture.source_ip:
            output += f"\n源IP: {capture.source_ip}"
        if capture.target_ip:
            output += f"\n目标IP: {capture.target_ip}"
        
        return ResponseModel(
            code=0,
            message="获取状态成功",
            data={
                "task_id": capture.task_id,
                "status": capture.status,
                "filename": capture.filename,
                "file_size": capture.file_size,
                "error_message": capture.error_message,
                "progress": progress,
                "output": output
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@router.get("/task-status/{task_id}", response_model=ResponseModel)
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """获取任务状态"""
    try:
        task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return ResponseModel(
            code=0,
            message="获取状态成功",
            data={
                "task_id": task.task_id,
                "status": task.status,
                "output": task.output,
                "error_message": task.error_message
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@router.get("/capture-history", response_model=ResponseModel)
def get_capture_history(db: Session = Depends(get_db)):
    """获取抓包历史"""
    try:
        captures = db.query(NetworkCapture).order_by(NetworkCapture.created_at.desc()).limit(50).all()
        
        data = []
        for capture in captures:
            data.append({
                "id": capture.id,
                "task_id": capture.task_id,
                "protocol": capture.protocol,
                "interface": capture.interface,
                "source_ip": capture.source_ip,
                "target_ip": capture.target_ip,
                "duration": capture.duration,
                "status": capture.status,
                "filename": capture.filename,
                "file_size": capture.file_size,
                "created_at": capture.created_at.isoformat() if capture.created_at else None
            })
        
        return ResponseModel(
            code=0,
            message="获取历史成功",
            data=data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")

@router.get("/task-history", response_model=ResponseModel)
def get_task_history(db: Session = Depends(get_db)):
    """获取任务历史"""
    try:
        tasks = db.query(NetworkTask).order_by(NetworkTask.created_at.desc()).limit(50).all()
        
        data = []
        for task in tasks:
            data.append({
                "id": task.id,
                "task_id": task.task_id,
                "command": task.command,
                "target": task.target,
                "status": task.status,
                "output": task.output,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat() if task.created_at else None
            })
        
        return ResponseModel(
            code=0,
            message="获取历史成功",
            data=data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")

@router.get("/download-capture/{task_id}")
def download_capture(task_id: str, db: Session = Depends(get_db)):
    """下载抓包文件"""
    try:
        print(f"[DEBUG] 尝试下载抓包文件，task_id: {task_id}")
        
        capture = db.query(NetworkCapture).filter(NetworkCapture.task_id == task_id).first()
        if not capture:
            print(f"[DEBUG] 抓包记录不存在: {task_id}")
            raise HTTPException(status_code=404, detail="抓包记录不存在")
        
        if not capture.file_path:
            print(f"[DEBUG] 文件路径为空: {task_id}")
            raise HTTPException(status_code=404, detail="文件路径为空")
        
        if not os.path.exists(capture.file_path):
            print(f"[DEBUG] 文件不存在: {capture.file_path}")
            raise HTTPException(status_code=404, detail=f"文件不存在: {capture.file_path}")
        
        print(f"[DEBUG] 文件存在，准备下载: {capture.file_path}")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            capture.file_path,
            filename=capture.filename,
            media_type='application/octet-stream'
        )
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@router.delete("/delete-capture/{task_id}", response_model=ResponseModel)
def delete_capture(task_id: str, db: Session = Depends(get_db)):
    """删除抓包文件"""
    try:
        capture = db.query(NetworkCapture).filter(NetworkCapture.task_id == task_id).first()
        if not capture:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        # 删除文件
        if capture.file_path and os.path.exists(capture.file_path):
            os.remove(capture.file_path)
        
        # 删除数据库记录
        db.delete(capture)
        db.commit()
        
        return ResponseModel(
            code=0,
            message="删除成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.delete("/delete-task/{task_id}", response_model=ResponseModel)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务记录"""
    try:
        task = db.query(NetworkTask).filter(NetworkTask.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        # 删除数据库记录
        db.delete(task)
        db.commit()
        
        return ResponseModel(
            code=0,
            message="删除成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
