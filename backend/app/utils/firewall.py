import subprocess
import os
from datetime import datetime
from typing import List, Dict, Any
from app.core.config import settings

def run_nft_command(command: List[str]) -> Dict[str, Any]:
    """执行nft命令"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "命令执行超时",
            "returncode": -1
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }

def get_firewall_status() -> Dict[str, Any]:
    """获取防火墙状态"""
    try:
        print(f"[DEBUG] 开始获取防火墙状态...")
        
        # 检查是否为容器环境
        is_container = os.path.exists('/.dockerenv') or (os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup', 'r').read())
        print(f"[DEBUG] 容器环境检测结果: {is_container}")
        
        if is_container:
            print(f"[DEBUG] 容器环境：使用nft命令检查")
            # 容器环境：直接检查nft规则
            rules_result = run_nft_command(['nft', 'list', 'ruleset'])
            is_running = rules_result["success"] and "table inet filter" in rules_result["stdout"]
            
            rules_count = 0
            if rules_result["success"]:
                rules_count = len([line for line in rules_result["stdout"].split('\n') 
                                 if line.strip() and not line.startswith('#')])
            
            print(f"[DEBUG] 容器环境防火墙状态: is_running={is_running}, rules_count={rules_count}")
            return {
                "is_running": is_running,
                "rules_count": rules_count,
                "last_updated": datetime.utcnow(),
                "environment": "container"
            }
        else:
            print(f"[DEBUG] 宿主机环境：使用systemctl检查")
            # 直接部署环境：使用systemctl
            if not os.path.exists('/usr/bin/systemctl'):
                print(f"[DEBUG] systemctl不存在于 /usr/bin/systemctl")
                return {
                    "is_running": False,
                    "rules_count": 0,
                    "last_updated": datetime.utcnow(),
                    "error": "系统不支持systemctl",
                    "environment": "unknown"
                }
            
            print(f"[DEBUG] systemctl存在，开始检查nftables服务状态")
            result = subprocess.run(
                ['systemctl', 'is-active', 'nftables'],
                capture_output=True,
                text=True
            )
            print(f"[DEBUG] systemctl命令执行结果: returncode={result.returncode}, stdout='{result.stdout.strip()}', stderr='{result.stderr.strip()}'")
            
            is_running = result.stdout.strip() == "active"
            
            # 获取规则数量
            rules_result = run_nft_command(['nft', 'list', 'ruleset'])
            rules_count = 0
            if rules_result["success"]:
                rules_count = len([line for line in rules_result["stdout"].split('\n') 
                                 if line.strip() and not line.startswith('#')])
            
            print(f"[DEBUG] 宿主机环境防火墙状态: is_running={is_running}, rules_count={rules_count}")
            return {
                "is_running": is_running,
                "rules_count": rules_count,
                "last_updated": datetime.utcnow(),
                "environment": "host"
            }
    except Exception as e:
        print(f"[DEBUG] 获取防火墙状态异常: {e}")
        import traceback
        traceback.print_exc()
        return {
            "is_running": False,
            "rules_count": 0,
            "last_updated": datetime.utcnow(),
            "error": str(e),
            "environment": "unknown"
        }

def reload_nftables(db_session=None) -> bool:
    """重新加载nftables配置"""
    try:
        print(f"[DEBUG] 开始重新加载nftables...")
        
        if db_session:
            # 使用数据库中的规则同步到应用专用链
            from app.utils.nftables_generator import NftablesGenerator
            generator = NftablesGenerator(db_session)
            print(f"[DEBUG] 使用规则生成器同步规则到应用专用链")
            return generator.sync_rules_from_db()
        
        # 检查是否为容器环境
        is_container = os.path.exists('/.dockerenv') or (os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup', 'r').read())
        print(f"[DEBUG] 容器环境检测结果: {is_container}")
        
        if is_container:
            print(f"[DEBUG] 容器环境：直接重新加载配置")
            # 容器环境：直接重新加载配置
            result = run_nft_command(['nft', '-f', settings.nftables_config_path])
            print(f"[DEBUG] 容器环境重新加载结果: {result}")
            return result["success"]
        else:
            print(f"[DEBUG] 宿主机环境：使用systemctl")
            # 直接部署环境：使用systemctl
            if not os.path.exists('/usr/bin/systemctl'):
                print(f"[DEBUG] systemctl不存在，尝试直接重新加载配置")
                result = run_nft_command(['nft', '-f', settings.nftables_config_path])
                print(f"[DEBUG] 直接重新加载结果: {result}")
                return result["success"]
            
            print(f"[DEBUG] systemctl存在，开始重新加载配置")
            # 重新加载配置文件
            result = run_nft_command(['nft', '-f', settings.nftables_config_path])
            if not result["success"]:
                print(f"[DEBUG] 重新加载nftables失败: {result['stderr']}")
                return False
            
            print(f"[DEBUG] 配置文件重新加载成功，开始重启nftables服务")
            # 重启nftables服务
            service_result = subprocess.run(
                ['systemctl', 'restart', 'nftables'],
                capture_output=True,
                text=True
            )
            
            print(f"[DEBUG] systemctl restart nftables结果: returncode={service_result.returncode}, stdout='{service_result.stdout.strip()}', stderr='{service_result.stderr.strip()}'")
            return service_result.returncode == 0
    except Exception as e:
        print(f"[DEBUG] 重新加载nftables异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_nftables_blacklist(db) -> bool:
    """更新nftables黑名单配置"""
    try:
        from app.db.models import BlacklistIP
        
        # 获取所有活跃的黑名单IP
        blacklist_ips = db.query(BlacklistIP).filter(BlacklistIP.is_active == True).all()
        
        # 生成nftables配置
        config_content = generate_nftables_config(blacklist_ips)
        
        # 写入配置文件
        with open(settings.nftables_config_path, 'w') as f:
            f.write(config_content)
        
        # 重新加载配置
        return reload_nftables()
    except Exception as e:
        print(f"更新nftables黑名单失败: {e}")
        return False

def generate_nftables_config(blacklist_ips: List) -> str:
    """生成nftables配置文件内容"""
    config = """#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    set blacklist {
        type ipv4_addr
        flags interval
        auto-merge
"""
    
    # 添加黑名单IP
    for ip in blacklist_ips:
        config += f"        {ip.ip_address}\n"
    
    config += """    }

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
    return config

def add_firewall_rule(rule_name: str, rule_content: str, rule_type: str) -> bool:
    """添加防火墙规则"""
    try:
        # 这里可以根据需要实现动态添加规则的逻辑
        # 目前简单地将规则写入配置文件
        config_path = settings.nftables_config_path
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            
            # 在适当位置插入新规则
            if rule_type == "input":
                # 在input链中添加规则
                insert_pos = content.find("chain input {")
                if insert_pos != -1:
                    # 找到链的结束位置
                    chain_start = content.find("{", insert_pos)
                    chain_end = content.find("}", chain_start)
                    
                    new_content = (
                        content[:chain_end] + 
                        f"\n        {rule_content}\n" +
                        content[chain_end:]
                    )
                    
                    with open(config_path, 'w') as f:
                        f.write(new_content)
                    
                    return reload_nftables()
        
        return False
    except Exception as e:
        print(f"添加防火墙规则失败: {e}")
        return False

def remove_firewall_rule(rule_name: str) -> bool:
    """删除防火墙规则"""
    try:
        # 这里实现删除规则的逻辑
        # 由于规则可能分散在配置文件中，这里简化处理
        return reload_nftables()
    except Exception as e:
        print(f"删除防火墙规则失败: {e}")
        return False
