#!/usr/bin/env python3
"""
数据库初始化脚本
创建默认管理员用户和基础数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal, engine
from app.db.models import Base, User, SystemLog
from app.core.config import settings
from passlib.context import CryptContext
from init_firewall import create_basic_nftables_config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def init_database():
    """初始化数据库"""
    print("正在创建数据库表...")
    
    # 初始化防火墙配置
    try:
        print("正在初始化防火墙配置...")
        create_basic_nftables_config()
        print("✅ 防火墙配置初始化完成")
    except Exception as e:
        print(f"⚠️  防火墙配置初始化失败: {e}")
    
    # 确保数据库目录存在
    db_path = "/opt/yk-safe/backend/yk_safe.db"
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"✅ 创建数据库目录: {db_dir}")
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"❌ 创建数据库表失败: {e}")
        return False
    
    db = SessionLocal()
    try:
        # 检查是否已存在管理员用户
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if not admin_user:
            print("正在创建默认管理员用户...")
            
            # 创建管理员用户
            admin_user = User(
                username="admin",
                email="admin@yksafe.local",
                hashed_password=get_password_hash("admin123"),
                is_active=True
            )
            db.add(admin_user)
            
            # 添加初始系统日志
            init_log = SystemLog(
                level="info",
                message="系统初始化完成，默认管理员用户已创建",
                source="system"
            )
            db.add(init_log)
            
            db.commit()
            print("✅ 默认管理员用户创建成功")
            print("   用户名: admin")
            print("   密码: admin123")
        else:
            print("✅ 管理员用户已存在，跳过创建")
        
        print("✅ 数据库初始化完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)
