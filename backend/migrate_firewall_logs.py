#!/usr/bin/env python3
"""
防火墙日志数据库迁移脚本
用于更新现有的防火墙日志表结构
"""

import sqlite3
import os
import sys
from datetime import datetime

def migrate_firewall_logs():
    """迁移防火墙日志表结构"""
    
    # 数据库文件路径
    db_path = "app.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("💡 请确保在正确的目录中运行此脚本")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🚀 开始迁移防火墙日志表...")
        print("=" * 50)
        
        # 检查当前表结构
        cursor.execute("PRAGMA table_info(firewall_logs)")
        current_columns = {col[1] for col in cursor.fetchall()}
        
        print(f"📋 当前列: {', '.join(sorted(current_columns))}")
        
        # 需要添加的新列
        new_columns = [
            ("source_port", "INTEGER"),
            ("destination_port", "INTEGER"),
            ("rule_id", "INTEGER"),
            ("rule_name", "TEXT"),
            ("interface", "TEXT"),
            ("packet_size", "INTEGER"),
            ("tcp_flags", "TEXT"),
            ("country", "TEXT"),
            ("city", "TEXT"),
            ("isp", "TEXT"),
            ("threat_level", "TEXT"),
            ("description", "TEXT")
        ]
        
        # 需要重命名的列
        rename_columns = [
            ("port", "destination_port")  # 将原来的port列重命名为destination_port
        ]
        
        # 创建新表
        print("\n🔧 创建新的防火墙日志表...")
        
        # 删除旧表（如果存在）
        cursor.execute("DROP TABLE IF EXISTS firewall_logs_new")
        
        # 创建新表
        create_table_sql = """
        CREATE TABLE firewall_logs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_ip TEXT,
            destination_ip TEXT,
            protocol TEXT,
            source_port INTEGER,
            destination_port INTEGER,
            action TEXT,
            rule_id INTEGER,
            rule_name TEXT,
            interface TEXT,
            packet_size INTEGER,
            tcp_flags TEXT,
            country TEXT,
            city TEXT,
            isp TEXT,
            threat_level TEXT,
            description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_table_sql)
        
        # 创建索引
        print("📊 创建索引...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_firewall_logs_source_ip ON firewall_logs_new(source_ip)",
            "CREATE INDEX IF NOT EXISTS idx_firewall_logs_destination_ip ON firewall_logs_new(destination_ip)",
            "CREATE INDEX IF NOT EXISTS idx_firewall_logs_protocol ON firewall_logs_new(protocol)",
            "CREATE INDEX IF NOT EXISTS idx_firewall_logs_action ON firewall_logs_new(action)",
            "CREATE INDEX IF NOT EXISTS idx_firewall_logs_timestamp ON firewall_logs_new(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_firewall_logs_threat_level ON firewall_logs_new(threat_level)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # 迁移数据
        print("📦 迁移现有数据...")
        
        # 检查是否有旧数据需要迁移
        cursor.execute("SELECT COUNT(*) FROM firewall_logs")
        old_count = cursor.fetchone()[0]
        
        if old_count > 0:
            # 迁移现有数据
            migrate_sql = """
            INSERT INTO firewall_logs_new (
                id, source_ip, destination_ip, protocol, 
                destination_port, action, timestamp
            )
            SELECT 
                id, source_ip, destination_ip, protocol, 
                port, action, timestamp
            FROM firewall_logs
            """
            
            cursor.execute(migrate_sql)
            print(f"✅ 迁移了 {old_count} 条记录")
        else:
            print("ℹ️  没有现有数据需要迁移")
        
        # 删除旧表并重命名新表
        print("🔄 更新表结构...")
        cursor.execute("DROP TABLE firewall_logs")
        cursor.execute("ALTER TABLE firewall_logs_new RENAME TO firewall_logs")
        
        # 验证新表结构
        cursor.execute("PRAGMA table_info(firewall_logs)")
        new_columns = {col[1] for col in cursor.fetchall()}
        
        print(f"📋 新列: {', '.join(sorted(new_columns))}")
        
        # 提交更改
        conn.commit()
        
        print("\n✅ 防火墙日志表迁移完成！")
        print("=" * 50)
        
        # 显示表信息
        cursor.execute("SELECT COUNT(*) FROM firewall_logs")
        total_count = cursor.fetchone()[0]
        print(f"📊 总记录数: {total_count}")
        
        # 显示表结构
        cursor.execute("PRAGMA table_info(firewall_logs)")
        columns = cursor.fetchall()
        print("\n📋 表结构:")
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULLABLE'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

def create_sample_logs():
    """创建一些示例日志数据用于测试"""
    
    db_path = "app.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n📝 创建示例日志数据...")
        
        # 插入一些示例日志
        sample_logs = [
            (
                "192.168.1.100", "10.0.0.1", "tcp", 12345, 80, "drop",
                None, None, "eth0", 1500, "SYN", "中国", "北京", "电信",
                "medium", "示例: 阻止的HTTP连接尝试"
            ),
            (
                "203.0.113.45", "10.0.0.1", "tcp", 54321, 22, "drop",
                None, None, "eth0", 1200, "SYN", "美国", "纽约", "Comcast",
                "high", "示例: 阻止的SSH连接尝试"
            ),
            (
                "8.8.8.8", "10.0.0.1", "udp", 12345, 53, "accept",
                None, None, "eth0", 512, None, "美国", "加利福尼亚", "Google",
                "low", "示例: 允许的DNS查询"
            ),
            (
                "172.16.0.50", "10.0.0.1", "icmp", None, None, "drop",
                None, None, "eth0", 84, None, "本地", "本地网络", "本地",
                "medium", "示例: 阻止的ICMP包"
            )
        ]
        
        insert_sql = """
        INSERT INTO firewall_logs (
            source_ip, destination_ip, protocol, source_port, destination_port,
            action, rule_id, rule_name, interface, packet_size, tcp_flags,
            country, city, isp, threat_level, description, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for log_data in sample_logs:
            cursor.execute(insert_sql, log_data + (datetime.now(),))
        
        conn.commit()
        print(f"✅ 创建了 {len(sample_logs)} 条示例日志")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建示例日志失败: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 防火墙日志数据库迁移工具")
    print("=" * 50)
    
    # 执行迁移
    if migrate_firewall_logs():
        # 询问是否创建示例数据
        try:
            choice = input("\n❓ 是否创建示例日志数据用于测试？(y/N): ").strip().lower()
            if choice in ['y', 'yes']:
                create_sample_logs()
        except KeyboardInterrupt:
            print("\n\n👋 用户取消操作")
        except Exception as e:
            print(f"\n❌ 创建示例数据时出错: {e}")
        
        print("\n🎉 迁移完成！现在可以启动应用并测试防火墙日志功能了。")
    else:
        print("\n❌ 迁移失败，请检查错误信息并重试。")
        sys.exit(1)
