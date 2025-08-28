#!/usr/bin/env python3
"""
添加防火墙配置表迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def add_firewall_config_table():
    """添加防火墙配置表"""
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # 检查表是否存在
        result = conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='firewall_config'
        """))
        
        if not result.fetchone():
            print("防火墙配置表不存在，创建新表...")
            conn.execute(text("""
                CREATE TABLE firewall_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode VARCHAR DEFAULT 'blacklist',
                    description TEXT,
                    updated_at DATETIME,
                    updated_by VARCHAR
                )
            """))
            
            # 插入默认配置
            conn.execute(text("""
                INSERT INTO firewall_config (mode, description, updated_by)
                VALUES ('blacklist', '默认黑名单模式', 'system')
            """))
            
            conn.commit()
            print("防火墙配置表创建成功，已插入默认配置")
        else:
            print("防火墙配置表已存在")
        
        # 检查firewall_rules表是否需要更新
        result = conn.execute(text("PRAGMA table_info(firewall_rules)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'rule_content' in columns:
            print("检测到旧的firewall_rules表结构，需要更新...")
            # 这里可以添加更新逻辑
            print("请运行 update_firewall_rules.py 来更新firewall_rules表结构")

if __name__ == "__main__":
    add_firewall_config_table()
