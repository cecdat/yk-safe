from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
import subprocess
import os
import shutil
import zipfile
import hashlib
import requests
from datetime import datetime
import uuid

from app.db.database import get_db
from app.db.models import SystemBackup, PushConfig, User
from app.schemas.settings import PasswordChange, PushConfigCreate, BackupResponse
from app.schemas.common import ResponseModel

router = APIRouter()

@router.post("/change-password", response_model=ResponseModel)
def change_password(password_data: PasswordChange, db: Session = Depends(get_db)):
    """修改密码"""
    try:
        # 获取当前用户（这里简化处理，实际应该从JWT token获取）
        user = db.query(User).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 验证旧密码
        old_password_hash = hashlib.sha256(password_data.old_password.encode()).hexdigest()
        if user.hashed_password != old_password_hash:
            raise HTTPException(status_code=400, detail="当前密码错误")
        
        # 更新新密码
        new_password_hash = hashlib.sha256(password_data.new_password.encode()).hexdigest()
        user.hashed_password = new_password_hash
        db.commit()
        
        return ResponseModel(
            code=0,
            message="密码修改成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"密码修改失败: {str(e)}")

@router.post("/create-backup", response_model=ResponseModel)
def create_backup(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """创建数据备份"""
    try:
        backup_id = str(uuid.uuid4())
        
        # 创建备份记录
        backup = SystemBackup(
            backup_id=backup_id,
            filename=f"backup_{backup_id}.zip",
            status='running'
        )
        db.add(backup)
        db.commit()
        
        # 在后台执行备份任务
        background_tasks.add_task(run_backup_task, backup_id, db)
        
        return ResponseModel(
            code=0,
            message="备份任务已启动",
            data={"backup_id": backup_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建备份失败: {str(e)}")

def run_backup_task(backup_id: str, db: Session):
    """执行备份任务"""
    try:
        backup_path = f"/tmp/backup_{backup_id}.zip"
        
        # 创建ZIP文件
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 备份数据库文件
            db_path = "/opt/yk-safe/backend/app.db"
            if os.path.exists(db_path):
                zipf.write(db_path, "app.db")
                print(f"备份数据库文件: {db_path}")
            else:
                print(f"数据库文件不存在: {db_path}")
            
            # 备份配置文件
            config_path = "/etc/nftables.conf"
            if os.path.exists(config_path):
                zipf.write(config_path, "nftables.conf")
                print(f"备份配置文件: {config_path}")
            else:
                print(f"配置文件不存在: {config_path}")
            
            # 备份预置配置文件
            presets_dir = "/etc/nftables-presets"
            if os.path.exists(presets_dir):
                for file in os.listdir(presets_dir):
                    file_path = os.path.join(presets_dir, file)
                    if os.path.isfile(file_path):
                        zipf.write(file_path, f"nftables-presets/{file}")
                        print(f"备份预置配置文件: {file_path}")
            else:
                print(f"预置配置目录不存在: {presets_dir}")
            
            # 添加一个说明文件
            info_content = f"""YK-Safe 系统备份
备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
备份ID: {backup_id}
包含文件:
- app.db (数据库文件)
- nftables.conf (防火墙配置)
- nftables-presets/ (预置配置文件)
"""
            zipf.writestr("backup_info.txt", info_content)
        
        # 检查文件是否创建成功
        if not os.path.exists(backup_path):
            raise Exception("备份文件创建失败")
        
        file_size = os.path.getsize(backup_path)
        print(f"备份文件创建成功: {backup_path}, 大小: {file_size} 字节")
        
        # 更新备份记录
        backup = db.query(SystemBackup).filter(SystemBackup.backup_id == backup_id).first()
        if backup:
            backup.status = 'completed'
            backup.file_path = backup_path
            backup.file_size = file_size
            db.commit()
            print(f"备份记录更新成功: {backup_id}")
        
    except Exception as e:
        print(f"备份任务失败: {str(e)}")
        backup = db.query(SystemBackup).filter(SystemBackup.backup_id == backup_id).first()
        if backup:
            backup.status = 'failed'
            backup.error_message = str(e)
            db.commit()

@router.get("/backup-history", response_model=ResponseModel)
def get_backup_history(db: Session = Depends(get_db)):
    """获取备份历史"""
    try:
        backups = db.query(SystemBackup).order_by(SystemBackup.created_at.desc()).all()
        
        data = []
        for backup in backups:
            data.append({
                "id": backup.id,
                "filename": backup.filename,
                "size": backup.file_size or 0,
                "created_at": backup.created_at,
                "status": backup.status
            })
        
        return ResponseModel(
            code=0,
            message="获取备份历史成功",
            data=data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取备份历史失败: {str(e)}")

@router.get("/download-backup/{backup_id}")
def download_backup(backup_id: int, db: Session = Depends(get_db)):
    """下载备份文件"""
    try:
        backup = db.query(SystemBackup).filter(SystemBackup.id == backup_id).first()
        if not backup or not backup.file_path or not os.path.exists(backup.file_path):
            raise HTTPException(status_code=404, detail="备份文件不存在")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            backup.file_path,
            filename=backup.filename,
            media_type='application/zip'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@router.delete("/delete-backup/{backup_id}", response_model=ResponseModel)
def delete_backup(backup_id: int, db: Session = Depends(get_db)):
    """删除备份文件"""
    try:
        backup = db.query(SystemBackup).filter(SystemBackup.id == backup_id).first()
        if not backup:
            raise HTTPException(status_code=404, detail="备份记录不存在")
        
        # 删除文件
        if backup.file_path and os.path.exists(backup.file_path):
            os.remove(backup.file_path)
        
        # 删除数据库记录
        db.delete(backup)
        db.commit()
        
        return ResponseModel(
            code=0,
            message="删除成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.post("/restore-backup/{backup_id}", response_model=ResponseModel)
def restore_backup(backup_id: int, db: Session = Depends(get_db)):
    """恢复备份"""
    try:
        backup = db.query(SystemBackup).filter(SystemBackup.id == backup_id).first()
        if not backup or not backup.file_path or not os.path.exists(backup.file_path):
            raise HTTPException(status_code=404, detail="备份文件不存在")
        
        # 解压备份文件
        temp_dir = f"/tmp/restore_{backup_id}"
        os.makedirs(temp_dir, exist_ok=True)
        
        with zipfile.ZipFile(backup.file_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # 恢复数据库
        db_file = os.path.join(temp_dir, "app.db")
        if os.path.exists(db_file):
            shutil.copy2(db_file, "/opt/yk-safe/backend/app.db")
        
        # 恢复配置文件
        nftables_file = os.path.join(temp_dir, "nftables.conf")
        if os.path.exists(nftables_file):
            shutil.copy2(nftables_file, "/etc/nftables.conf")
        
        # 恢复预置配置文件
        presets_dir = os.path.join(temp_dir, "nftables-presets")
        if os.path.exists(presets_dir):
            shutil.rmtree("/etc/nftables-presets", ignore_errors=True)
            shutil.copytree(presets_dir, "/etc/nftables-presets")
        
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return ResponseModel(
            code=0,
            message="恢复成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")

@router.get("/push-config", response_model=ResponseModel)
def get_push_config(db: Session = Depends(get_db)):
    """获取推送配置"""
    try:
        config = db.query(PushConfig).first()
        if not config:
            # 创建默认配置
            config = PushConfig()
            db.add(config)
            db.commit()
        
        return ResponseModel(
            code=0,
            message="获取推送配置成功",
            data={
                "webhook_enabled": config.webhook_enabled,
                "webhook_url": config.webhook_url,
                "webhook_types": config.webhook_types.split(',') if config.webhook_types else [],
                "bark_enabled": config.bark_enabled,
                "bark_url": config.bark_url,
                "bark_types": config.bark_types.split(',') if config.bark_types else []
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推送配置失败: {str(e)}")

@router.post("/push-config", response_model=ResponseModel)
def save_push_config(config_data: PushConfigCreate, db: Session = Depends(get_db)):
    """保存推送配置"""
    try:
        config = db.query(PushConfig).first()
        if not config:
            config = PushConfig()
            db.add(config)
        
        config.webhook_enabled = config_data.webhook_enabled
        config.webhook_url = config_data.webhook_url
        config.webhook_types = ','.join(config_data.webhook_types) if config_data.webhook_types else None
        config.bark_enabled = config_data.bark_enabled
        config.bark_url = config_data.bark_url
        config.bark_types = ','.join(config_data.bark_types) if config_data.bark_types else None
        
        db.commit()
        
        return ResponseModel(
            code=0,
            message="推送配置保存成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存推送配置失败: {str(e)}")

@router.post("/test-push", response_model=ResponseModel)
def test_push(push_data: Dict[str, Any]):
    """测试推送"""
    try:
        success_count = 0
        error_messages = []
        
        # 测试Webhook推送
        if push_data.get('webhook_enabled') and push_data.get('webhook_url'):
            try:
                webhook_data = {
                    "msg_type": "text",
                    "content": {
                        "text": "这是一条测试消息，来自YK-Safe系统"
                    }
                }
                
                response = requests.post(
                    push_data['webhook_url'],
                    json=webhook_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    success_count += 1
                else:
                    error_messages.append(f"Webhook推送失败: {response.status_code}")
            except Exception as e:
                error_messages.append(f"Webhook推送错误: {str(e)}")
        
        # 测试Bark推送
        if push_data.get('bark_enabled') and push_data.get('bark_url'):
            try:
                bark_url = push_data['bark_url']
                if not bark_url.endswith('/'):
                    bark_url += '/'
                
                test_url = f"{bark_url}测试消息/来自YK-Safe系统的测试推送"
                
                response = requests.get(test_url, timeout=10)
                
                if response.status_code == 200:
                    success_count += 1
                else:
                    error_messages.append(f"Bark推送失败: {response.status_code}")
            except Exception as e:
                error_messages.append(f"Bark推送错误: {str(e)}")
        
        if success_count > 0:
            return ResponseModel(
                code=0,
                message=f"测试推送成功 ({success_count}个渠道)",
                data={"errors": error_messages} if error_messages else None
            )
        else:
            raise Exception("所有推送渠道都失败了: " + "; ".join(error_messages))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试推送失败: {str(e)}")
