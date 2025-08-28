#!/usr/bin/env python3
"""
防火墙规则表结构更新迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def update_firewall_rules_table():
    """更新防火墙规则表结构"""
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # 检查表是否存在
        result = conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='firewall_rules'
        """))
        
        if not result.fetchone():
            print("防火墙规则表不存在，创建新表...")
            conn.execute(text("""
                CREATE TABLE firewall_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name VARCHAR UNIQUE NOT NULL,
                    protocol VARCHAR,
                    source VARCHAR,
                    destination VARCHAR,
                    port VARCHAR,
                    action VARCHAR,
                    rule_type VARCHAR,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            """))
            conn.commit()
            print("防火墙规则表创建成功")
            return
        
        # 检查是否需要更新表结构
        result = conn.execute(text("PRAGMA table_info(firewall_rules)"))
        columns = [row[1] for row in result.fetchall()]
        
        print(f"当前表结构: {columns}")
        
        # 添加新列
        new_columns = [
            ('protocol', 'VARCHAR'),
            ('source', 'VARCHAR'),
            ('destination', 'VARCHAR'),
            ('port', 'VARCHAR'),
            ('action', 'VARCHAR'),
            ('description', 'TEXT'),
            ('updated_at', 'DATETIME')
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                print(f"添加列: {col_name}")
                conn.execute(text(f"ALTER TABLE firewall_rules ADD COLUMN {col_name} {col_type}"))
        
        # 删除旧列
        if 'rule_content' in columns:
            print("删除旧列: rule_content")
            # SQLite不支持直接删除列，需要重建表
            conn.execute(text("""
                CREATE TABLE firewall_rules_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name VARCHAR UNIQUE NOT NULL,
                    protocol VARCHAR,
                    source VARCHAR,
                    destination VARCHAR,
                    port VARCHAR,
                    action VARCHAR,
                    rule_type VARCHAR,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            """))
            
            # 复制数据
            conn.execute(text("""
                INSERT INTO firewall_rules_new (id, rule_name, rule_type, is_active, created_at)
                SELECT id, rule_name, rule_type, is_active, created_at
                FROM firewall_rules
            """))
            
            # 删除旧表，重命名新表
            conn.execute(text("DROP TABLE firewall_rules"))
            conn.execute(text("ALTER TABLE firewall_rules_new RENAME TO firewall_rules"))
        
        conn.commit()
        print("防火墙规则表结构更新完成")

if __name__ == "__main__":
    update_firewall_rules_table()
