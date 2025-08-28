#!/usr/bin/env python3
"""
防火墙初始化脚本
创建基本的nftables配置
"""

import os
import subprocess
from app.core.config import settings

def create_basic_nftables_config():
    """创建基本的nftables配置"""
    config_content = """#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    set blacklist {
        type ipv4_addr
        flags interval
        auto-merge
    }

    chain input {
        type filter hook input priority 0; policy accept;
        
        # 拒绝黑名单IP
        ip saddr @blacklist drop
        
        # 允许本地回环
        iif lo accept
        
        # 允许已建立的连接
        ct state established,related accept
        
        # 允许SSH (端口22)
        tcp dport 22 accept
        
        # 允许HTTP (端口80)
        tcp dport 80 accept
        
        # 允许HTTPS (端口443)
        tcp dport 443 accept
        
        # 允许自定义端口 (5023, 8000)
        tcp dport 5023 accept
        tcp dport 8000 accept
        
        # 记录被拒绝的连接
        log prefix "nftables denied: " group 0
        
        # 拒绝其他所有连接
        drop
    }

    chain forward {
        type filter hook forward priority 0; policy accept;
    }

    chain output {
        type filter hook output priority 0; policy accept;
    }
}
"""
    
    # 确保配置目录存在
    config_dir = os.path.dirname(settings.nftables_config_path)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    
    # 写入配置文件
    with open(settings.nftables_config_path, 'w') as f:
        f.write(config_content)
    
    print(f"✅ 防火墙配置文件已创建: {settings.nftables_config_path}")

def enable_nftables_service():
    """启用nftables服务"""
    try:
        # 启用nftables服务
        result = subprocess.run(
            ['systemctl', 'enable', 'nftables'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ nftables服务已启用")
        else:
            print(f"⚠️  启用nftables服务失败: {result.stderr}")
            
    except Exception as e:
        print(f"⚠️  启用nftables服务异常: {e}")

def start_nftables_service():
    """启动nftables服务"""
    try:
        # 启动nftables服务
        result = subprocess.run(
            ['systemctl', 'start', 'nftables'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ nftables服务已启动")
        else:
            print(f"⚠️  启动nftables服务失败: {result.stderr}")
            
    except Exception as e:
        print(f"⚠️  启动nftables服务异常: {e}")

def reload_nftables_config():
    """重新加载nftables配置"""
    try:
        # 重新加载配置文件
        result = subprocess.run(
            ['nft', '-f', settings.nftables_config_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ nftables配置已重新加载")
        else:
            print(f"⚠️  重新加载nftables配置失败: {result.stderr}")
            
    except Exception as e:
        print(f"⚠️  重新加载nftables配置异常: {e}")

def check_nftables_status():
    """检查nftables状态"""
    try:
        # 检查服务状态
        result = subprocess.run(
            ['systemctl', 'is-active', 'nftables'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            status = result.stdout.strip()
            print(f"📊 nftables服务状态: {status}")
            
            if status == "active":
                # 检查规则
                rules_result = subprocess.run(
                    ['nft', 'list', 'ruleset'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if rules_result.returncode == 0:
                    rules_count = len([line for line in rules_result.stdout.split('\n') 
                                     if line.strip() and not line.startswith('#')])
                    print(f"📊 当前规则数量: {rules_count}")
                else:
                    print("⚠️  无法获取规则列表")
        else:
            print("❌ nftables服务未运行")
            
    except Exception as e:
        print(f"⚠️  检查nftables状态异常: {e}")

def main():
    """主函数"""
    print("🚀 开始初始化防火墙...")
    
    # 创建基本配置
    create_basic_nftables_config()
    
    # 启用服务
    enable_nftables_service()
    
    # 启动服务
    start_nftables_service()
    
    # 重新加载配置
    reload_nftables_config()
    
    # 检查状态
    check_nftables_status()
    
    print("✅ 防火墙初始化完成！")

if __name__ == "__main__":
    main()
