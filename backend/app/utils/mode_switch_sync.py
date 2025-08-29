#!/usr/bin/env python3
"""
模式切换后的规则同步工具
"""

import subprocess
import os
import logging
from typing import List
from sqlalchemy.orm import Session
from app.db.models import FirewallRule

logger = logging.getLogger(__name__)

def sync_rules_after_mode_switch(db: Session, new_mode: str):
    """
    模式切换后同步规则到新的配置
    
    Args:
        db: 数据库会话
        new_mode: 新的防火墙模式 ("blacklist" 或 "whitelist")
    """
    try:
        logger.info(f"开始同步规则到{new_mode}模式...")
        
        # 获取所有活跃的防火墙规则
        rules = db.query(FirewallRule).filter(FirewallRule.is_active == True).all()
        logger.info(f"从数据库获取到 {len(rules)} 条活跃规则")
        
        # 清空应用专用链
        logger.info("清空应用专用链...")
        result = subprocess.run(
            ['nft', 'flush', 'chain', 'inet', 'filter', 'YK_SAFE_CHAIN'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"清空应用专用链失败: {result.stderr}")
            return False
        
        # 根据模式添加规则
        success_count = 0
        for rule in rules:
            if add_rule_to_chain(rule, new_mode):
                success_count += 1
            else:
                logger.error(f"添加规则失败: {rule.rule_name}")
        
        logger.info(f"规则同步完成: {success_count}/{len(rules)} 条规则成功添加")
        return success_count == len(rules)
        
    except Exception as e:
        logger.error(f"规则同步失败: {e}")
        return False

def add_rule_to_chain(rule, mode: str) -> bool:
    """
    添加规则到应用专用链
    
    Args:
        rule: 防火墙规则对象
        mode: 防火墙模式
    """
    try:
        # 构建规则条件
        conditions = []
        
        if rule.source and rule.source != "0.0.0.0/0":
            conditions.append(f"ip saddr {rule.source}")
        
        if rule.destination and rule.destination != "0.0.0.0/0":
            conditions.append(f"ip daddr {rule.destination}")
        
        if rule.protocol and rule.port:
            clean_protocol = rule.protocol.replace("protocol ", "").strip()
            if clean_protocol in ["tcp", "udp"]:
                conditions.append(f"{clean_protocol} dport {rule.port}")
        
        # 根据模式确定动作
        if mode == "blacklist":
            # 黑名单模式：所有规则都是阻止连接
            action = "drop"
        else:  # whitelist mode
            # 白名单模式：根据规则动作决定
            if rule.action == "accept":
                action = "accept"
            else:
                action = "drop"
        
        # 构建nft命令
        command = ['nft', 'add', 'rule', 'inet', 'filter', 'YK_SAFE_CHAIN']
        if conditions:
            command.extend(conditions)
        command.append(action)
        
        # 执行命令
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"成功添加规则: {rule.rule_name}")
            return True
        else:
            logger.error(f"添加规则失败: {rule.rule_name}, 错误: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"添加规则时出错: {rule.rule_name}, 错误: {e}")
        return False

def backup_current_config():
    """
    备份当前配置
    """
    try:
        if os.path.exists('/etc/nftables.conf'):
            import shutil
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"/etc/nftables.conf.backup.{timestamp}"
            shutil.copy2('/etc/nftables.conf', backup_path)
            logger.info(f"已备份当前配置到: {backup_path}")
            return backup_path
        return None
    except Exception as e:
        logger.error(f"备份配置失败: {e}")
        return None

def restore_config_from_backup(backup_path: str):
    """
    从备份恢复配置
    
    Args:
        backup_path: 备份文件路径
    """
    try:
        if os.path.exists(backup_path):
            import shutil
            shutil.copy2(backup_path, '/etc/nftables.conf')
            
            # 应用恢复的配置
            result = subprocess.run(
                ['nft', '-f', '/etc/nftables.conf'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("配置恢复成功")
                return True
            else:
                logger.error(f"配置恢复失败: {result.stderr}")
                return False
        else:
            logger.error(f"备份文件不存在: {backup_path}")
            return False
    except Exception as e:
        logger.error(f"恢复配置失败: {e}")
        return False
