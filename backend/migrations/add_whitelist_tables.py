#!/usr/bin/env python3
"""
添加白名单相关表的数据库迁移脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models import Base, WhitelistToken, WhitelistRequest

def create_whitelist_tables():
    """创建白名单相关表"""
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    inspector = inspect(engine)
    
    print("🔧 开始创建白名单相关表...")
    
    # 检查whitelist_tokens表是否存在
    if not inspector.has_table("whitelist_tokens"):
        print("📋 创建 whitelist_tokens 表...")
        WhitelistToken.__table__.create(engine)
        print("✅ whitelist_tokens 表创建成功")
    else:
        print("ℹ️ whitelist_tokens 表已存在")
    
    # 检查whitelist_requests表是否存在
    if not inspector.has_table("whitelist_requests"):
        print("📋 创建 whitelist_requests 表...")
        WhitelistRequest.__table__.create(engine)
        print("✅ whitelist_requests 表创建成功")
    else:
        print("ℹ️ whitelist_requests 表已存在")
    
    # 创建示例Token
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 检查是否已有Token
        existing_token = db.query(WhitelistToken).first()
        if not existing_token:
            print("📝 创建示例Token...")
            from datetime import datetime, timedelta
            
            sample_token = WhitelistToken(
                token="demo_token_123456789",
                company_name="示例公司",
                description="用于演示的示例Token",
                max_uses=100,
                used_count=0,
                expires_at=datetime.utcnow() + timedelta(days=365),
                is_active=True,
                auto_approve=False,
                created_by="system"
            )
            
            db.add(sample_token)
            db.commit()
            print("✅ 示例Token创建成功")
            print(f"   Token: demo_token_123456789")
            print(f"   公司: 示例公司")
            print(f"   过期时间: {sample_token.expires_at}")
        else:
            print("ℹ️ 已存在Token，跳过创建示例Token")
            
    except Exception as e:
        print(f"❌ 创建示例Token失败: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("🎉 白名单相关表创建完成！")
    print("")
    print("📝 使用说明:")
    print("1. 访问 /whitelist.html 进行白名单申请")
    print("2. 使用示例Token: demo_token_123456789")
    print("3. 在管理后台审核申请")
    print("4. 通过后会自动创建防火墙规则")

if __name__ == "__main__":
    create_whitelist_tables()
