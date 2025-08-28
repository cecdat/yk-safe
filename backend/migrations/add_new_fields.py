#!/usr/bin/env python3
"""
添加新字段的数据库迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

def add_new_fields():
    """添加新字段到现有表"""
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    inspector = inspect(engine)
    
    print("🔧 开始添加新字段...")
    
    # 检查并添加whitelist_tokens表的auto_approve字段
    if inspector.has_table("whitelist_tokens"):
        columns = [col['name'] for col in inspector.get_columns("whitelist_tokens")]
        if 'auto_approve' not in columns:
            print("📋 添加 whitelist_tokens.auto_approve 字段...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE whitelist_tokens ADD COLUMN auto_approve BOOLEAN DEFAULT FALSE"))
                    conn.commit()
                print("✅ whitelist_tokens.auto_approve 字段添加成功")
            except Exception as e:
                print(f"❌ 添加 auto_approve 字段失败: {e}")
        else:
            print("ℹ️ whitelist_tokens.auto_approve 字段已存在")
    
    # 检查并添加firewall_rules表的source_type字段
    if inspector.has_table("firewall_rules"):
        columns = [col['name'] for col in inspector.get_columns("firewall_rules")]
        if 'source_type' not in columns:
            print("📋 添加 firewall_rules.source_type 字段...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE firewall_rules ADD COLUMN source_type VARCHAR DEFAULT 'manual'"))
                    conn.commit()
                print("✅ firewall_rules.source_type 字段添加成功")
            except Exception as e:
                print(f"❌ 添加 source_type 字段失败: {e}")
        else:
            print("ℹ️ firewall_rules.source_type 字段已存在")
    
    print("🎉 新字段添加完成！")

if __name__ == "__main__":
    add_new_fields()
