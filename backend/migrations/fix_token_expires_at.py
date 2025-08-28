#!/usr/bin/env python3
"""
修复WhitelistToken表的expires_at字段约束
将expires_at字段从NOT NULL改为允许NULL
"""

import sqlite3
import os
from pathlib import Path

def fix_token_expires_at():
    """修复WhitelistToken表的expires_at字段约束"""
    
    # 获取数据库文件路径
    db_path = Path(__file__).parent.parent / "firewall.db"
    
    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查当前表结构
        cursor.execute("PRAGMA table_info(whitelist_tokens)")
        columns = cursor.fetchall()
        
        # 查找expires_at字段
        expires_at_column = None
        for col in columns:
            if col[1] == 'expires_at':
                expires_at_column = col
                break
        
        if not expires_at_column:
            print("未找到expires_at字段")
            return False
        
        # 检查是否已经是nullable
        if expires_at_column[3] == 0:  # 0表示NOT NULL
            print("正在修复expires_at字段约束...")
            
            # 创建临时表
            cursor.execute("""
                CREATE TABLE whitelist_tokens_temp (
                    id INTEGER PRIMARY KEY,
                    token VARCHAR NOT NULL,
                    company_name VARCHAR NOT NULL,
                    description TEXT,
                    max_uses INTEGER DEFAULT 100,
                    used_count INTEGER DEFAULT 0,
                    expires_at DATETIME,
                    is_active BOOLEAN DEFAULT 1,
                    auto_approve BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR,
                    updated_at DATETIME
                )
            """)
            
            # 复制数据
            cursor.execute("""
                INSERT INTO whitelist_tokens_temp 
                SELECT id, token, company_name, description, max_uses, used_count, 
                       expires_at, is_active, auto_approve, created_at, created_by, updated_at
                FROM whitelist_tokens
            """)
            
            # 删除原表
            cursor.execute("DROP TABLE whitelist_tokens")
            
            # 重命名临时表
            cursor.execute("ALTER TABLE whitelist_tokens_temp RENAME TO whitelist_tokens")
            
            # 重新创建索引
            cursor.execute("CREATE UNIQUE INDEX ix_whitelist_tokens_token ON whitelist_tokens (token)")
            cursor.execute("CREATE INDEX ix_whitelist_tokens_id ON whitelist_tokens (id)")
            
            conn.commit()
            print("✅ expires_at字段约束修复成功")
        else:
            print("✅ expires_at字段已经是nullable，无需修复")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    print("开始修复WhitelistToken表的expires_at字段约束...")
    success = fix_token_expires_at()
    if success:
        print("修复完成")
    else:
        print("修复失败")
