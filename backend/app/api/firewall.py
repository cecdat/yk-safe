from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import subprocess
import os
from datetime import datetime

from app.db.database import get_db
from app.db.models import FirewallRule, FirewallLog, FirewallConfig
from app.schemas.firewall import FirewallRuleCreate, FirewallRuleUpdate, FirewallRuleResponse, FirewallStatus, FirewallConfigResponse, FirewallModeUpdate
from app.schemas.common import ResponseModel
from app.utils.firewall import get_firewall_status, reload_nftables
from app.utils.nftables_generator import NftablesGenerator
from app.utils.nftables_sync_service import force_sync
from app.core.config import settings

router = APIRouter()

@router.get("/status", response_model=ResponseModel)
def get_status(db: Session = Depends(get_db)):
    """获取防火墙状态"""
    try:
        status = get_firewall_status()
        rules_count = db.query(FirewallRule).filter(FirewallRule.is_active == True).count()
        
        return ResponseModel(
            code=0,
            message="获取防火墙状态成功",
            data={
                "is_running": status["is_running"],
                "rules_count": rules_count,
                "last_updated": status["last_updated"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取防火墙状态失败: {str(e)}")

@router.post("/start", response_model=ResponseModel)
def start_firewall(db: Session = Depends(get_db)):
    """启动防火墙"""
    try:
        print(f"[DEBUG] 开始启动防火墙...")
        
        # 检查是否为容器环境
        is_container = os.path.exists('/.dockerenv') or (os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup', 'r').read())
        print(f"[DEBUG] 容器环境检测结果: {is_container}")
        
        if is_container:
            print(f"[DEBUG] 容器环境：使用nft命令启动")
            # 容器环境：直接使用nft命令
            result = subprocess.run(
                ['nft', 'flush', 'ruleset'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            print(f"[DEBUG] nft flush ruleset结果: returncode={result.returncode}, stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}'")
            
            if result.returncode == 0:
                print(f"[DEBUG] 容器环境防火墙启动成功，开始重新加载配置")
                # 重新加载配置
                reload_nftables()
                return ResponseModel(
                    code=0,
                    message="防火墙启动成功 (容器模式)",
                    data={"is_running": True}
                )
            else:
                print(f"[DEBUG] 容器环境防火墙启动失败: {result.stderr}")
                return ResponseModel(
                    code=5000,
                    message=f"防火墙启动失败 (容器模式): {result.stderr}",
                    data={"is_running": False}
                )
        else:
            print(f"[DEBUG] 宿主机环境：使用systemctl启动")
            # 直接部署环境：使用systemctl
            print(f"[DEBUG] 检查systemctl命令...")
            
            if not os.path.exists('/usr/bin/systemctl'):
                print(f"[DEBUG] systemctl不存在于 /usr/bin/systemctl")
                return ResponseModel(
                    code=5000,
                    message="系统不支持systemctl，无法启动防火墙服务",
                    data={"is_running": False}
                )
            
            print(f"[DEBUG] systemctl存在，开始启动nftables服务")
            result = subprocess.run(
                ['systemctl', 'start', 'nftables'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            print(f"[DEBUG] systemctl start nftables结果: returncode={result.returncode}, stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}'")
            
            if result.returncode == 0:
                print(f"[DEBUG] 宿主机环境防火墙启动成功，开始重新加载配置")
                # 重新加载配置
                reload_nftables()
                return ResponseModel(
                    code=0,
                    message="防火墙启动成功",
                    data={"is_running": True}
                )
            else:
                print(f"[DEBUG] 宿主机环境防火墙启动失败: {result.stderr}")
                return ResponseModel(
                    code=5000,
                    message=f"防火墙启动失败: {result.stderr}",
                    data={"is_running": False}
                )
    except subprocess.TimeoutExpired:
        print(f"[DEBUG] 防火墙启动超时")
        return ResponseModel(
            code=5000,
            message="防火墙启动超时",
            data={"is_running": False}
        )
    except Exception as e:
        print(f"[DEBUG] 防火墙启动异常: {e}")
        import traceback
        traceback.print_exc()
        return ResponseModel(
            code=5000,
            message=f"防火墙启动失败: {str(e)}",
            data={"is_running": False}
        )

@router.post("/stop", response_model=ResponseModel)
def stop_firewall(db: Session = Depends(get_db)):
    """停止防火墙"""
    try:
        print(f"[DEBUG] 开始停止防火墙...")
        
        # 检查是否为容器环境
        is_container = os.path.exists('/.dockerenv') or (os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup', 'r').read())
        print(f"[DEBUG] 容器环境检测结果: {is_container}")
        
        if is_container:
            print(f"[DEBUG] 容器环境：使用nft命令停止")
            # 容器环境：直接使用nft命令
            result = subprocess.run(
                ['nft', 'flush', 'ruleset'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            print(f"[DEBUG] nft flush ruleset结果: returncode={result.returncode}, stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}'")
            
            if result.returncode == 0:
                print(f"[DEBUG] 容器环境防火墙停止成功")
                return ResponseModel(
                    code=0,
                    message="防火墙停止成功 (容器模式)",
                    data={"is_running": False}
                )
            else:
                print(f"[DEBUG] 容器环境防火墙停止失败: {result.stderr}")
                return ResponseModel(
                    code=5000,
                    message=f"防火墙停止失败 (容器模式): {result.stderr}",
                    data={"is_running": True}
                )
        else:
            print(f"[DEBUG] 宿主机环境：使用systemctl停止")
            # 直接部署环境：使用systemctl
            print(f"[DEBUG] 检查systemctl命令...")
            
            if not os.path.exists('/usr/bin/systemctl'):
                print(f"[DEBUG] systemctl不存在于 /usr/bin/systemctl")
                return ResponseModel(
                    code=5000,
                    message="系统不支持systemctl，无法停止防火墙服务",
                    data={"is_running": True}
                )
            
            print(f"[DEBUG] systemctl存在，开始停止nftables服务")
            result = subprocess.run(
                ['systemctl', 'stop', 'nftables'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            print(f"[DEBUG] systemctl stop nftables结果: returncode={result.returncode}, stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}'")
            
            if result.returncode == 0:
                print(f"[DEBUG] 宿主机环境防火墙停止成功")
                return ResponseModel(
                    code=0,
                    message="防火墙停止成功",
                    data={"is_running": False}
                )
            else:
                print(f"[DEBUG] 宿主机环境防火墙停止失败: {result.stderr}")
                return ResponseModel(
                    code=5000,
                    message=f"防火墙停止失败: {result.stderr}",
                    data={"is_running": True}
                )
    except subprocess.TimeoutExpired:
        print(f"[DEBUG] 防火墙停止超时")
        return ResponseModel(
            code=5000,
            message="防火墙停止超时",
            data={"is_running": True}
        )
    except Exception as e:
        print(f"[DEBUG] 防火墙停止异常: {e}")
        import traceback
        traceback.print_exc()
        return ResponseModel(
            code=5000,
            message=f"防火墙停止失败: {str(e)}",
            data={"is_running": True}
        )

@router.post("/restart", response_model=ResponseModel)
def restart_firewall(db: Session = Depends(get_db)):
    """重启防火墙"""
    try:
        print(f"[DEBUG] 开始重启防火墙...")
        
        # 检查是否为容器环境
        is_container = os.path.exists('/.dockerenv') or (os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup', 'r').read())
        print(f"[DEBUG] 容器环境检测结果: {is_container}")
        
        if is_container:
            print(f"[DEBUG] 容器环境：先停止再启动")
            # 容器环境：先停止再启动
            stop_result = subprocess.run(
                ['nft', 'flush', 'ruleset'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            print(f"[DEBUG] nft flush ruleset结果: returncode={stop_result.returncode}, stdout='{stop_result.stdout.strip()}', stderr='{stop_result.stderr.strip()}'")
            
            if stop_result.returncode == 0:
                print(f"[DEBUG] 容器环境防火墙停止成功，开始重新加载配置")
                # 重新加载配置
                reload_nftables()
                return ResponseModel(
                    code=0,
                    message="防火墙重启成功 (容器模式)",
                    data={"is_running": True}
                )
            else:
                print(f"[DEBUG] 容器环境防火墙停止失败: {stop_result.stderr}")
                return ResponseModel(
                    code=5000,
                    message=f"防火墙重启失败 (容器模式): {stop_result.stderr}",
                    data={"is_running": False}
                )
        else:
            print(f"[DEBUG] 宿主机环境：使用systemctl重启")
            # 直接部署环境：使用systemctl
            print(f"[DEBUG] 检查systemctl命令...")
            
            if not os.path.exists('/usr/bin/systemctl'):
                print(f"[DEBUG] systemctl不存在于 /usr/bin/systemctl")
                return ResponseModel(
                    code=5000,
                    message="系统不支持systemctl，无法重启防火墙服务",
                    data={"is_running": False}
                )
            
            print(f"[DEBUG] systemctl存在，开始重启nftables服务")
            result = subprocess.run(
                ['systemctl', 'restart', 'nftables'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            print(f"[DEBUG] systemctl restart nftables结果: returncode={result.returncode}, stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}'")
            
            if result.returncode == 0:
                print(f"[DEBUG] 宿主机环境防火墙重启成功，开始重新加载配置")
                # 重新加载配置
                reload_nftables()
                return ResponseModel(
                    code=0,
                    message="防火墙重启成功",
                    data={"is_running": True}
                )
            else:
                print(f"[DEBUG] 宿主机环境防火墙重启失败: {result.stderr}")
                return ResponseModel(
                    code=5000,
                    message=f"防火墙重启失败: {result.stderr}",
                    data={"is_running": False}
                )
    except subprocess.TimeoutExpired:
        print(f"[DEBUG] 防火墙重启超时")
        return ResponseModel(
            code=5000,
            message="防火墙重启超时",
            data={"is_running": False}
        )
    except Exception as e:
        print(f"[DEBUG] 防火墙重启异常: {e}")
        import traceback
        traceback.print_exc()
        return ResponseModel(
            code=5000,
            message=f"防火墙重启失败: {str(e)}",
            data={"is_running": False}
        )

@router.get("/rules", response_model=ResponseModel)
def get_firewall_rules(db: Session = Depends(get_db)):
    """获取所有防火墙规则"""
    rules = db.query(FirewallRule).filter(FirewallRule.is_active == True).all()
    
    return ResponseModel(
        code=0,
        message="获取防火墙规则成功",
        data=[{
            "id": rule.id,
            "rule_name": rule.rule_name,
            "protocol": rule.protocol,
            "source": rule.source,
            "destination": rule.destination,
            "port": rule.port,
            "action": rule.action,
            "rule_type": rule.rule_type,
            "description": rule.description,
            "is_active": rule.is_active,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at
        } for rule in rules]
    )

@router.post("/rules", response_model=ResponseModel)
def add_firewall_rule(rule: FirewallRuleCreate, db: Session = Depends(get_db)):
    """添加防火墙规则"""
    # 检查规则名是否已存在（只检查活跃的规则）
    existing_rule = db.query(FirewallRule).filter(
        FirewallRule.rule_name == rule.rule_name,
        FirewallRule.is_active == True
    ).first()
    
    if existing_rule:
        raise HTTPException(status_code=400, detail="规则名已存在")
    
    # 检查是否有已删除的同名规则，如果有则更新它而不是创建新的
    deleted_rule = db.query(FirewallRule).filter(
        FirewallRule.rule_name == rule.rule_name,
        FirewallRule.is_active == False
    ).first()
    
    if deleted_rule:
        # 重新激活已删除的规则
        deleted_rule.protocol = rule.protocol
        deleted_rule.source = rule.source
        deleted_rule.destination = rule.destination
        deleted_rule.port = rule.port
        deleted_rule.action = rule.action
        deleted_rule.rule_type = rule.rule_type
        deleted_rule.description = rule.description
        deleted_rule.source_type = getattr(rule, 'source_type', 'manual')
        deleted_rule.is_active = True
        deleted_rule.created_at = datetime.utcnow()
        
        db.commit()
        db.refresh(deleted_rule)
        db_rule = deleted_rule
    else:
        # 创建新规则
        db_rule = FirewallRule(
            rule_name=rule.rule_name,
            protocol=rule.protocol,
            source=rule.source,
            destination=rule.destination,
            port=rule.port,
            action=rule.action,
            rule_type=rule.rule_type,
            description=rule.description,
            source_type=getattr(rule, 'source_type', 'manual')
        )
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)
    
    # 实时应用规则（如果选择立即生效）
    if getattr(rule, 'apply_immediately', True):
        try:
            generator = NftablesGenerator(db)
            if generator.add_rule_realtime(db_rule):
                print(f"实时添加规则成功: {db_rule.rule_name}")
            else:
                print(f"实时添加规则失败: {db_rule.rule_name}")
        except Exception as e:
            print(f"实时添加规则失败: {e}")
    
    return ResponseModel(
        code=0,
        message="添加防火墙规则成功",
        data={
            "id": db_rule.id,
            "rule_name": db_rule.rule_name,
            "protocol": db_rule.protocol,
            "action": db_rule.action,
            "rule_type": db_rule.rule_type
        }
    )

@router.put("/rules/{rule_id}", response_model=ResponseModel)
def update_firewall_rule(rule_id: int, rule_update: FirewallRuleUpdate, db: Session = Depends(get_db)):
    """更新防火墙规则"""
    rule = db.query(FirewallRule).filter(FirewallRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="防火墙规则不存在")
    
    # 检查规则名是否已存在（如果更新规则名）
    if rule_update.rule_name and rule_update.rule_name != rule.rule_name:
        existing_rule = db.query(FirewallRule).filter(
            FirewallRule.rule_name == rule_update.rule_name,
            FirewallRule.is_active == True
        ).first()
        if existing_rule:
            raise HTTPException(status_code=400, detail="规则名已存在")
    
    # 更新规则字段
    update_data = rule_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    db.refresh(rule)
    
    # 实时更新规则（如果选择立即生效）
    if getattr(rule_update, 'apply_immediately', True):
        try:
            generator = NftablesGenerator(db)
            # 创建旧规则对象用于删除
            old_rule = FirewallRule(
                rule_name=rule.rule_name,
                protocol=rule.protocol,
                source=rule.source,
                destination=rule.destination,
                port=rule.port,
                action=rule.action,
                rule_type=rule.rule_type
            )
            
            if generator.update_rule_realtime(old_rule, rule):
                print(f"实时更新规则成功: {rule.rule_name}")
            else:
                print(f"实时更新规则失败: {rule.rule_name}")
        except Exception as e:
            print(f"实时更新规则失败: {e}")
    
    return ResponseModel(
        code=0,
        message="更新防火墙规则成功",
        data={
            "id": rule.id,
            "rule_name": rule.rule_name,
            "protocol": rule.protocol,
            "action": rule.action,
            "rule_type": rule.rule_type
        }
    )

@router.delete("/rules/{rule_id}", response_model=ResponseModel)
def delete_firewall_rule(rule_id: int, db: Session = Depends(get_db)):
    """删除防火墙规则"""
    rule = db.query(FirewallRule).filter(FirewallRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="防火墙规则不存在")
    
    # 软删除
    rule.is_active = False
    db.commit()
    
    # 实时删除规则（删除规则总是立即生效）
    try:
        generator = NftablesGenerator(db)
        if generator.delete_rule_realtime(rule):
            print(f"实时删除规则成功: {rule.rule_name}")
        else:
            print(f"实时删除规则失败: {rule.rule_name}")
    except Exception as e:
        print(f"实时删除规则失败: {e}")
    
    return ResponseModel(
        code=0,
        message="删除防火墙规则成功",
        data={"rule_name": rule.rule_name}
    )

@router.post("/reload", response_model=ResponseModel)
def reload_firewall(db: Session = Depends(get_db)):
    """重新加载防火墙配置"""
    try:
        reload_nftables()
        return ResponseModel(
            code=0,
            message="重新加载防火墙配置成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新加载防火墙配置失败: {str(e)}")

@router.post("/sync", response_model=ResponseModel)
def sync_to_persistent(db: Session = Depends(get_db)):
    """将实时规则同步到持久化配置文件"""
    try:
        if force_sync():
            return ResponseModel(
                code=0,
                message="实时规则同步到持久化配置成功"
            )
        else:
            raise HTTPException(status_code=500, detail="同步失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")

@router.get("/sync/status", response_model=ResponseModel)
def get_sync_status():
    """获取同步服务状态"""
    try:
        from app.utils.nftables_sync_service import get_sync_status
        status = get_sync_status()
        return ResponseModel(
            code=0,
            message="获取同步状态成功",
            data=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")

@router.get("/logs", response_model=ResponseModel)
def get_firewall_logs(db: Session = Depends(get_db), limit: int = 100):
    """获取防火墙日志"""
    logs = db.query(FirewallLog).order_by(FirewallLog.created_at.desc()).limit(limit).all()
    
    return ResponseModel(
        code=0,
        message="获取防火墙日志成功",
        data=[{
            "id": log.id,
            "source_ip": log.source_ip,
            "action": log.action,
            "rule_name": log.rule_name,
            "created_at": log.created_at
        } for log in logs]
    )

@router.get("/config", response_model=ResponseModel)
def get_firewall_config(db: Session = Depends(get_db)):
    """获取防火墙配置"""
    config = db.query(FirewallConfig).first()
    if not config:
        # 创建默认配置
        config = FirewallConfig(mode="blacklist", description="默认黑名单模式")
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return ResponseModel(
        code=0,
        message="获取防火墙配置成功",
        data={
            "id": config.id,
            "mode": config.mode,
            "description": config.description,
            "updated_at": config.updated_at,
            "updated_by": config.updated_by
        }
    )

@router.put("/config/mode", response_model=ResponseModel)
def update_firewall_mode(mode_update: FirewallModeUpdate, db: Session = Depends(get_db)):
    """更新防火墙模式"""
    if mode_update.mode not in ["blacklist", "whitelist"]:
        raise HTTPException(status_code=400, detail="无效的模式，只支持 blacklist 或 whitelist")
    
    config = db.query(FirewallConfig).first()
    if not config:
        config = FirewallConfig()
        db.add(config)
    
    old_mode = config.mode
    config.mode = mode_update.mode
    config.description = mode_update.description
    config.updated_by = "admin"  # 这里可以从JWT token中获取用户信息
    
    db.commit()
    db.refresh(config)
    
    # 重新加载nftables配置
    try:
        reload_nftables(db)
    except Exception as e:
        print(f"重新加载nftables失败: {e}")
    
    return ResponseModel(
        code=0,
        message=f"防火墙模式已从 {old_mode} 切换到 {mode_update.mode}",
        data={
            "id": config.id,
            "mode": config.mode,
            "description": config.description,
            "updated_at": config.updated_at,
            "updated_by": config.updated_by
        }
    )
