import os
import subprocess
import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import FirewallRule, BlacklistIP, FirewallConfig

# 配置日志
logger = logging.getLogger(__name__)

class NftablesGenerator:
    """nftables规则生成器 - 双层架构"""
    
    def __init__(self, db: Session):
        self.db = db
        self.config_file = "/etc/nftables.conf"
        self.backup_file = "/etc/nftables.conf.backup"
        # 使用 raw 表处理黑名单规则，确保最高优先级
        self.raw_table_name = "raw"
        self.filter_table_name = "filter"
        self.prerouting_chain_name = "prerouting"
        self.input_chain_name = "input"
        # 应用专用链名称
        self.app_chain_name = "YK_SAFE_CHAIN"
    
    def generate_config(self) -> str:
        """生成nftables配置文件内容"""
        # 获取防火墙配置
        config = self.db.query(FirewallConfig).first()
        if not config:
            config = FirewallConfig(mode="blacklist", description="默认黑名单模式")
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        
        # 获取所有活跃的防火墙规则
        rules = self.db.query(FirewallRule).filter(FirewallRule.is_active == True).all()
        
        # 获取所有活跃的黑名单IP
        blacklist_ips = self.db.query(BlacklistIP).filter(BlacklistIP.is_active == True).all()
        
        # 生成配置文件内容
        config_content = self._generate_base_config(config.mode, blacklist_ips)
        # 将规则插入到input链中
        config_content = self._insert_rules_into_chain(config_content, rules, config.mode)
        
        return config_content
    
    def _generate_base_config(self, mode: str = "blacklist", blacklist_ips: List[BlacklistIP] = None) -> str:
        """生成基础配置"""
        if mode == "blacklist":
            return self._generate_blacklist_config(blacklist_ips)
        elif mode == "whitelist":
            return self._generate_whitelist_config()
        else:
            raise ValueError(f"不支持的防火墙模式: {mode}")
    
    def _generate_blacklist_config(self, blacklist_ips: List[BlacklistIP] = None) -> str:
        """生成黑名单模式配置"""
        config = """#!/usr/sbin/nft -f

# 清空现有规则
flush ruleset

# 定义 raw 表 - 用于黑名单规则，确保最高优先级
table inet raw {
    # 黑名单IP集合
    set blacklist {
        type ipv4_addr
        flags interval
        auto-merge
"""
        
        # 添加黑名单IP
        if blacklist_ips:
            for ip in blacklist_ips:
                config += f"        {ip.ip_address}\n"
        
        config += """    }
    
    # 定义 prerouting 链 - 优先级 -300，确保最先执行
    chain prerouting {
        type filter hook prerouting priority -300; policy accept;
        
        # 黑名单规则 - 最高优先级，在 Docker 等网络组件之前执行
        ip saddr @blacklist drop
        
        # 允许本地回环
        iif lo accept
        
        # 允许已建立的连接
        ct state established,related accept
    }
}

# 定义 filter 表 - 用于应用层规则
table inet filter {
    # 定义链
    chain input {
        type filter hook input priority 0; policy accept;
        
        # 允许本地回环
        iif lo accept
        
        # 允许已建立的连接
        ct state established,related accept
        
        # 跳转到应用专用链
        jump YK_SAFE_CHAIN
        
        # Docker网络支持
        # 允许Docker默认网桥 (172.17.0.0/16)
        ip saddr 172.17.0.0/16 accept
        
        # 允许Docker自定义网络 (172.18.0.0/15, 172.20.0.0/14, 172.24.0.0/13, 172.32.0.0/11)
        ip saddr 172.18.0.0/15 accept
        ip saddr 172.20.0.0/14 accept
        ip saddr 172.24.0.0/13 accept
        ip saddr 172.32.0.0/11 accept
        
        # 允许Docker IPv6网络
        ip6 saddr fd00::/8 accept
    }
    
    # 应用专用链 - YK-Safe应用规则专用
    chain YK_SAFE_CHAIN {
        # 用户自定义规则占位符
        {{USER_RULES_PLACEHOLDER}}
        
        # 返回主链继续处理
        return
    }
    
    chain forward {
        type filter hook forward priority 0; policy accept;
        
        # 允许已建立的连接
        ct state established,related accept
        
        # Docker网络转发支持
        # 允许Docker默认网桥
        ip saddr 172.17.0.0/16 accept
        ip daddr 172.17.0.0/16 accept
        
        # 允许Docker自定义网络
        ip saddr 172.18.0.0/15 accept
        ip daddr 172.18.0.0/15 accept
        ip saddr 172.20.0.0/14 accept
        ip daddr 172.20.0.0/14 accept
        ip saddr 172.24.0.0/13 accept
        ip daddr 172.24.0.0/13 accept
        ip saddr 172.32.0.0/11 accept
        ip daddr 172.32.0.0/11 accept
        
        # 允许Docker IPv6网络
        ip6 saddr fd00::/8 accept
        ip6 daddr fd00::/8 accept
    }
    
    chain output {
        type filter hook output priority 0; policy accept;
        
        # Docker网络输出支持
        ip daddr 172.17.0.0/16 accept
        ip daddr 172.18.0.0/15 accept
        ip daddr 172.20.0.0/14 accept
        ip daddr 172.24.0.0/13 accept
        ip daddr 172.32.0.0/11 accept
        ip6 daddr fd00::/8 accept
    }
}
"""
        return config
    
    def _generate_whitelist_config(self) -> str:
        """生成白名单模式配置"""
        config = """#!/usr/sbin/nft -f

# 清空现有规则
flush ruleset

# 定义 filter 表 - 白名单模式：默认拒绝所有连接，只允许明确允许的IP
table inet filter {
    # 定义链
    chain input {
        type filter hook input priority 0; policy drop;
        
        # 允许本地回环
        iif lo accept
        
        # 允许已建立的连接
        ct state established,related accept
        
        # 跳转到应用专用链
        jump YK_SAFE_CHAIN
        
        # Docker网络支持 (白名单模式下必须明确允许)
        # 允许Docker默认网桥 (172.17.0.0/16)
        ip saddr 172.17.0.0/16 accept
        
        # 允许Docker自定义网络 (172.18.0.0/15, 172.20.0.0/14, 172.24.0.0/13, 172.32.0.0/11)
        ip saddr 172.18.0.0/15 accept
        ip saddr 172.20.0.0/14 accept
        ip saddr 172.24.0.0/13 accept
        ip saddr 172.32.0.0/11 accept
        
        # 允许Docker IPv6网络
        ip6 saddr fd00::/8 accept
        
        # 允许SSH (端口22)
        tcp dport 22 accept
        
        # 允许HTTP (端口80)
        tcp dport 80 accept
        
        # 允许HTTPS (端口443)
        tcp dport 443 accept
        
        # 允许前端端口 (5023)
        tcp dport 5023 accept

        # 允许前端端口 (5024)
        tcp dport 5024 accept

        # 允许后端端口 (8000)
        tcp dport 8000 accept
    }
    
    # 应用专用链 - YK-Safe应用规则专用
    chain YK_SAFE_CHAIN {
        # 白名单预置IP规则
        # 预置IP：120.226.208.2
        ip saddr 120.226.208.2 accept
        
        # 预置IP段：192.168.2.0/24
        ip saddr 192.168.2.0/24 accept
        
        # 用户自定义规则占位符
        {{USER_RULES_PLACEHOLDER}}
        
        # 白名单模式：默认拒绝所有其他连接
        drop
    }
    
    chain forward {
        type filter hook forward priority 0; policy drop;
        
        # 允许已建立的连接
        ct state established,related accept
        
        # Docker网络转发支持 (白名单模式下必须明确允许)
        # 允许Docker默认网桥
        ip saddr 172.17.0.0/16 accept
        ip daddr 172.17.0.0/16 accept
        
        # 允许Docker自定义网络
        ip saddr 172.18.0.0/15 accept
        ip daddr 172.18.0.0/15 accept
        ip saddr 172.20.0.0/14 accept
        ip daddr 172.20.0.0/14 accept
        ip saddr 172.24.0.0/13 accept
        ip daddr 172.24.0.0/13 accept
        ip saddr 172.32.0.0/11 accept
        ip daddr 172.32.0.0/11 accept
        
        # 允许Docker IPv6网络
        ip6 saddr fd00::/8 accept
        ip6 daddr fd00::/8 accept
    }
    
    chain output {
        type filter hook output priority 0; policy accept;
        
        # Docker网络输出支持
        ip daddr 172.17.0.0/16 accept
        ip daddr 172.18.0.0/15 accept
        ip daddr 172.20.0.0/14 accept
        ip daddr 172.24.0.0/13 accept
        ip daddr 172.32.0.0/11 accept
        ip6 daddr fd00::/8 accept
    }
}
"""
        return config
    
    def _insert_rules_into_chain(self, config_content: str, rules: List[FirewallRule], mode: str = "blacklist") -> str:
        """将用户自定义规则插入到filter表的input链中"""
        # 使用占位符替换，避免脆弱的字符串解析
        placeholder = "{{USER_RULES_PLACEHOLDER}}"
        
        if not rules:
            # 如果没有规则，移除占位符行，避免语法错误
            if placeholder in config_content:
                # 移除包含占位符的整行
                lines = config_content.split('\n')
                filtered_lines = []
                for line in lines:
                    if placeholder not in line:
                        filtered_lines.append(line)
                return '\n'.join(filtered_lines)
            else:
                return config_content
        
        # 生成规则文本
        rules_text = ""
        for rule in rules:
            rules_text += self._generate_rule_text(rule, mode)
        
        if placeholder in config_content:
            # 直接替换占位符
            return config_content.replace(placeholder, rules_text.rstrip())
        else:
            # 向后兼容：如果配置中没有占位符，使用原来的方法
            return self._insert_rules_into_chain_fallback(config_content, rules_text.rstrip())
    
    def _insert_rules_into_chain_fallback(self, config_content: str, rules_text: str) -> str:
        """向后兼容的规则插入方法（备用方案）"""
        try:
            # 找到filter表中input链的结束位置
            lines = config_content.split('\n')
            filter_input_chain_end = -1
            
            for i, line in enumerate(lines):
                if 'table inet filter' in line:
                    # 找到filter表的开始
                    for j in range(i, len(lines)):
                        if 'chain input {' in lines[j]:
                            # 找到input链的开始
                            brace_count = 0
                            for k in range(j, len(lines)):
                                if '{' in lines[k]:
                                    brace_count += 1
                                if '}' in lines[k]:
                                    brace_count -= 1
                                    if brace_count == 0:
                                        filter_input_chain_end = k
                                        break
                            break
                    break
            
            if filter_input_chain_end == -1:
                return config_content
            
            # 在filter表input链结束前插入规则
            lines.insert(filter_input_chain_end, rules_text)
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.warning(f"使用备用方案插入规则时出错: {e}")
            # 如果备用方案也失败，在文件末尾添加规则
            return config_content + "\n\n# 用户自定义规则\n" + rules_text
    
    def _generate_rule_text(self, rule: FirewallRule, mode: str = "blacklist") -> str:
        """生成单个规则的文本"""
        text = f"        # 规则: {rule.rule_name}\n"
        
        if rule.description:
            text += f"        # 描述: {rule.description}\n"
        
        # 构建规则条件 - 使用正确的nftables语法
        conditions = []
        
        # nftables规则语法：ip saddr 直接指定IP，不需要协议
        if rule.source and rule.source != "0.0.0.0/0":
            conditions.append(f"ip saddr {rule.source}")
        
        if rule.destination and rule.destination != "0.0.0/0":
            conditions.append(f"ip daddr {rule.destination}")
        
        # 如果需要特定协议和端口，可以添加
        if rule.protocol and rule.port:
            # 清理协议字段，移除可能的 "protocol " 前缀
            clean_protocol = rule.protocol.replace("protocol ", "").strip()
            if clean_protocol in ["tcp", "udp"]:
                conditions.append(f"{clean_protocol} dport {rule.port}")
        
        # 构建完整规则
        condition_str = " ".join(conditions)
        
        # 根据模式调整动作
        if mode == "blacklist":
            # 黑名单模式：所有规则都是阻止连接
            action = "drop"
        else:  # whitelist mode
            # 白名单模式：所有规则都应该是允许连接
            action = "accept"
        
        if conditions:
            text += f"        {condition_str} {action}\n"
        else:
            text += f"        {action}\n"
        
        text += "\n"
        return text
    
    def apply_config(self) -> bool:
        """应用配置文件"""
        try:
            # 生成配置内容
            config_content = self.generate_config()
            
            # 备份当前配置
            if os.path.exists(self.config_file):
                subprocess.run(['cp', self.config_file, self.backup_file], check=True)
            
            # 写入新配置
            with open(self.config_file, 'w') as f:
                f.write(config_content)
            
            # 测试配置
            result = subprocess.run(['nft', '-c', '-f', self.config_file], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"nftables配置测试失败: {result.stderr}")
                # 恢复备份
                if os.path.exists(self.backup_file):
                    subprocess.run(['cp', self.backup_file, self.config_file], check=True)
                return False
            
            # 应用配置
            result = subprocess.run(['nft', '-f', self.config_file], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"nftables配置应用失败: {result.stderr}")
                return False
            
            logger.info("nftables配置应用成功")
            return True
            
        except Exception as e:
            logger.error(f"应用nftables配置时出错: {e}")
            return False
    
    def reload_config(self) -> bool:
        """重新加载配置"""
        try:
            # 重新加载nftables服务
            result = subprocess.run(['systemctl', 'reload', 'nftables'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"重新加载nftables服务失败: {result.stderr}")
                return False
            
            logger.info("nftables配置重新加载成功")
            return True
            
        except Exception as e:
            logger.error(f"重新加载nftables配置时出错: {e}")
            return False

    # ==================== 实时操作层 ====================
    
    def add_rule_realtime(self, rule: FirewallRule) -> bool:
        """实时添加规则到应用专用链 - 立即生效"""
        try:
            # 确保基础架构存在
            if not self._ensure_infrastructure():
                logger.error("无法确保基础架构存在，跳过规则添加")
                return False
            
            # 构建nft命令 - 目标改为应用专用链
            nft_command = self._build_nft_add_command(rule)
            
            logger.info(f"执行添加命令: {' '.join(nft_command)}")
            
            # 执行命令
            result = subprocess.run(nft_command, capture_output=True, text=True, shell=False)
            
            if result.returncode != 0:
                logger.error(f"实时添加规则失败: {result.stderr}")
                # 添加规则失败，没有备用方案
                return False
            
            logger.info(f"✅ 实时添加规则成功: {rule.rule_name}")
            logger.info("⏰ 提示：规则变更将在30秒后完全生效，请耐心等待")
            return True
            
        except Exception as e:
            logger.error(f"实时添加规则时出错: {e}")
            return False
    
    def delete_rule_realtime(self, rule: FirewallRule) -> bool:
        """实时删除规则 - 立即生效"""
        try:
            # 确保基础架构存在
            if not self._ensure_infrastructure():
                logger.error("无法确保基础架构存在，跳过规则删除")
                return False
            
            # 获取规则的句柄
            rule_handle = self.get_rule_handle(rule)
            
            if rule_handle:
                # 使用句柄删除规则 - 目标改为应用专用链
                nft_command = [
                    'nft', 'delete', 'rule', 'inet', 
                    self.filter_table_name, self.app_chain_name, 
                    'handle', rule_handle
                ]
                result = subprocess.run(nft_command, capture_output=True, text=True, shell=False)
                
                if result.returncode != 0:
                    logger.error(f"实时删除规则失败: {result.stderr}")
                    return False
                
                logger.info(f"✅ 实时删除规则成功: {rule.rule_name}")
                logger.info("⏰ 提示：规则变更将在30秒后完全生效，请耐心等待")
                return True
            else:
                # 如果找不到句柄，尝试使用规则内容删除
                logger.info(f"未找到规则句柄，尝试使用规则内容删除: {rule.rule_name}")
                
                # 尝试使用内容删除作为备用方案
                if self._delete_rule_by_content(rule):
                    logger.info(f"✅ 实时删除规则成功: {rule.rule_name}")
                    logger.info("⏰ 提示：规则变更将在30秒后完全生效，请耐心等待")
                    return True
                else:
                    logger.error(f"❌ 实时删除规则失败: {rule.rule_name}")
                    return False
            
        except Exception as e:
            logger.error(f"实时删除规则时出错: {e}")
            return False
    
    def update_rule_realtime(self, old_rule: FirewallRule, new_rule: FirewallRule) -> bool:
        """实时更新规则 - 先删除旧规则，再添加新规则"""
        try:
            # 先删除旧规则
            if not self.delete_rule_realtime(old_rule):
                return False
            
            # 再添加新规则
            if not self.add_rule_realtime(new_rule):
                # 如果添加失败，尝试恢复旧规则
                self.add_rule_realtime(old_rule)
                return False
            
            logger.info(f"✅ 实时更新规则成功: {new_rule.rule_name}")
            logger.info("⏰ 提示：规则变更将在30秒后完全生效，请耐心等待")
            return True
            
        except Exception as e:
            logger.error(f"实时更新规则时出错: {e}")
            return False
    
    def _build_rule_conditions(self, rule: FirewallRule) -> List[str]:
        """构建规则条件列表 - 公共方法，消除代码重复"""
        conditions = []
        
        if rule.source and rule.source != "0.0.0.0/0":
            conditions.append(f"ip saddr {rule.source}")
        
        if rule.destination and rule.destination != "0.0.0.0/0":
            conditions.append(f"ip daddr {rule.destination}")
        
        if rule.protocol and rule.port:
            clean_protocol = rule.protocol.replace("protocol ", "").strip()
            if clean_protocol in ["tcp", "udp"]:
                conditions.append(f"{clean_protocol} dport {rule.port}")
        
        return conditions
    
    def _build_nft_add_command(self, rule: FirewallRule) -> str:
        """构建nft add命令"""
        # 构建规则条件
        conditions = []
        
        if rule.source and rule.source != "0.0.0.0/0":
            conditions.append(f"ip saddr {rule.source}")
        
        if rule.destination and rule.destination != "0.0.0/0/0":
            conditions.append(f"ip daddr {rule.destination}")
        
        if rule.protocol and rule.port:
            clean_protocol = rule.protocol.replace("protocol ", "").strip()
            if clean_protocol in ["tcp", "udp"]:
                conditions.append(f"{clean_protocol} dport {rule.port}")
        
        # 构建动作
        action = "drop" if rule.action == "drop" else "accept"
        
        # 构建完整命令
        condition_str = " ".join(conditions)
        if conditions:
            rule_text = f"{condition_str} {action}"
        else:
            rule_text = action
        
        # 用户自定义规则添加到应用专用链
        command = ['nft', 'add', 'rule', 'inet', self.filter_table_name, self.app_chain_name]
        # 安全地构建命令，避免split()拆分问题
        if conditions:
            command.extend(conditions)
        command.append(action)
        return command
    
    def _build_nft_delete_command(self, rule: FirewallRule) -> str:
        """构建nft delete命令 - 备用方案"""
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
        
        # 构建动作 - 根据规则动作决定
        if rule.action == "accept":
            action = "accept"
        else:
            action = "drop"
        
        # 构建完整命令
        condition_str = " ".join(conditions)
        
        # 注意：nft delete rule 不支持直接使用规则内容，应该使用句柄
        # 这里作为备用方案，但推荐使用 get_rule_handle 方法
        # 如果必须使用内容删除，需要先找到规则的索引位置
        if conditions:
            # 使用内容删除 - 目标改为应用专用链
            command = ['nft', 'delete', 'rule', 'inet', self.filter_table_name, self.app_chain_name]
            # 安全地构建命令，避免split()拆分问题
            command.extend(conditions)
            command.append(action)
            return command
        else:
            # 如果没有条件，直接删除动作规则 - 目标改为应用专用链
            command = ['nft', 'delete', 'rule', 'inet', self.filter_table_name, self.app_chain_name]
            command.append(action)
            return command
    
    def list_rules_realtime(self) -> List[str]:
        """实时列出应用专用链中的规则"""
        try:
            # 确保基础架构存在
            if not self._ensure_infrastructure():
                logger.error("无法确保基础架构存在，无法列出规则")
                return []
            
            result = subprocess.run(
                ['nft', 'list', 'chain', 'inet', self.filter_table_name, self.app_chain_name],
                capture_output=True, text=True, shell=False
            )
            
            if result.returncode != 0:
                logger.error(f"列出规则失败: {result.stderr}")
                return []
            
            return result.stdout.strip().split('\n')
            
        except Exception as e:
            logger.error(f"列出规则时出错: {e}")
            return []
    
    def flush_rules_realtime(self) -> bool:
        """实时清空应用专用链中的所有规则"""
        try:
            # 确保基础架构存在
            if not self._ensure_infrastructure():
                logger.error("无法确保基础架构存在，跳过规则清空")
                return False
            
            result = subprocess.run(
                ['nft', 'flush', 'chain', 'inet', self.filter_table_name, self.app_chain_name],
                capture_output=True, text=True, shell=False
            )
            
            if result.returncode != 0:
                logger.error(f"清空规则失败: {result.stderr}")
                return False
            
            logger.info("✅ 实时清空规则成功")
            logger.info("⏰ 提示：规则变更将在30秒后完全生效，请耐心等待")
            return True
            
        except Exception as e:
            logger.error(f"清空规则时出错: {e}")
            return False
    
    def sync_to_persistent(self) -> bool:
        """将实时规则同步到持久化配置文件"""
        try:
            # 获取当前实时规则
            current_rules = self.list_rules_realtime()
            
            # 生成新的配置文件
            config_content = self.generate_config()
            
            # 备份当前配置
            if os.path.exists(self.config_file):
                timestamp = int(time.time())
                backup_file = f"{self.backup_file}.{timestamp}"
                subprocess.run(['cp', self.config_file, backup_file], check=True)
            
            # 写入新配置
            with open(self.config_file, 'w') as f:
                f.write(config_content)
            
            logger.info("✅ 实时规则已同步到持久化配置文件")
            logger.info("⏰ 提示：配置同步完成，系统将在下次重启时使用新配置")
            return True
            
        except Exception as e:
            logger.error(f"同步到持久化配置时出错: {e}")
            return False
    
    def get_rule_handle(self, rule: FirewallRule) -> Optional[str]:
        """获取规则的句柄（用于精确删除）"""
        try:
            # 确保基础架构存在
            if not self._ensure_infrastructure():
                logger.error("无法确保基础架构存在，无法获取规则句柄")
                return None
            
            # 使用 -a 标志列出规则，确保包含句柄信息（-a 是 --handle 的简写）
            result = subprocess.run(
                ['nft', '-a', 'list', 'chain', 'inet', self.filter_table_name, self.app_chain_name],
                capture_output=True, text=True, shell=False
            )
            
            if result.returncode != 0:
                logger.error(f"列出规则句柄失败: {result.stderr}")
                return None
            
            rules = result.stdout.strip().split('\n')
            
            for rule_line in rules:
                if self._rule_matches(rule, rule_line):
                    # 提取句柄 - 格式通常是 "handle 123"
                    if 'handle' in rule_line:
                        # 使用正则表达式提取句柄数字
                        import re
                        handle_match = re.search(r'handle\s+(\d+)', rule_line)
                        if handle_match:
                            return handle_match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"获取规则句柄时出错: {e}")
            return None
    
    def _rule_matches(self, rule: FirewallRule, rule_line: str) -> bool:
        """检查规则是否匹配 - 使用精确的词元匹配"""
        # 跳过注释行和空行
        if rule_line.strip().startswith('#') or not rule_line.strip():
            return False
        
        # 将规则行分割成词元
        line_tokens = rule_line.split()
        
        # 检查源IP - 精确匹配词元
        if rule.source and rule.source != "0.0.0.0/0":
            source_pattern = f"ip saddr {rule.source}"
            source_tokens = source_pattern.split()
            if not self._tokens_contain_sequence(line_tokens, source_tokens):
                return False
        
        # 检查目标IP - 精确匹配词元
        if rule.destination and rule.destination != "0.0.0.0/0":
            dest_pattern = f"ip daddr {rule.destination}"
            dest_tokens = dest_pattern.split()
            if not self._tokens_contain_sequence(line_tokens, dest_tokens):
                return False
        
        # 检查协议和端口 - 精确匹配词元
        if rule.protocol and rule.port:
            clean_protocol = rule.protocol.replace("protocol ", "").strip()
            protocol_pattern = f"{clean_protocol} dport {rule.port}"
            protocol_tokens = protocol_pattern.split()
            if not self._tokens_contain_sequence(line_tokens, protocol_tokens):
                return False
        
        # 检查动作 - 精确匹配词元
        action = "drop" if rule.action == "drop" else "accept"
        if action not in line_tokens:
            return False
        
        # 确保这是一个实际的规则行（包含动作）
        if not any(keyword in line_tokens for keyword in ['accept', 'drop', 'reject']):
            return False
        
        return True
    
    def _tokens_contain_sequence(self, line_tokens: List[str], pattern_tokens: List[str]) -> bool:
        """检查词元序列是否包含在行词元中（连续匹配）"""
        if len(pattern_tokens) > len(line_tokens):
            return False
        
        for i in range(len(line_tokens) - len(pattern_tokens) + 1):
            if line_tokens[i:i + len(pattern_tokens)] == pattern_tokens:
                return True
        
        return False

    def _delete_rule_by_content(self, rule: FirewallRule) -> bool:
        """通过内容删除规则 - 备用方案"""
        try:
            # 确保基础架构存在
            if not self._ensure_infrastructure():
                logger.error("无法确保基础架构存在，无法删除规则")
                return False
            
            # 构建规则内容用于删除
            rule_content = self._build_rule_content_for_delete(rule)
            
            if not rule_content:
                logger.warning(f"无法构建规则内容: {rule.rule_name}")
                return False
            
            # 使用 nft delete rule 按内容删除 - 目标改为应用专用链
            # 注意：nft delete rule 需要完整的规则内容，包括所有条件
            nft_command = [
                'nft', 'delete', 'rule', 'inet', 
                self.filter_table_name, self.app_chain_name
            ]
            # 将规则内容按空格分割，确保每个参数都是独立的列表元素
            nft_command.extend(rule_content.split())
            
            logger.info(f"执行删除命令: {' '.join(nft_command)}")
            
            result = subprocess.run(nft_command, capture_output=True, text=True, shell=False)
            
            if result.returncode != 0:
                logger.error(f"通过内容删除规则失败: {result.stderr}")
                # 内容删除失败，没有其他备用方案
                return False
            
            logger.info(f"通过内容删除规则成功: {rule.rule_name}")
            return True
            
        except Exception as e:
            logger.error(f"通过内容删除规则时出错: {e}")
            return False
    
    def _build_rule_content_for_delete(self, rule: FirewallRule) -> str:
        """构建用于删除的规则内容"""
        try:
            # 构建规则条件 - 使用公共方法
            conditions = self._build_rule_conditions(rule)
            
            # 构建动作
            action = "drop" if rule.action == "drop" else "accept"
            
            # 构建完整规则内容
            if conditions:
                return f"{' '.join(conditions)} {action}"
            else:
                return action
                
        except Exception as e:
            logger.error(f"构建规则内容时出错: {e}")
            return ""

    def _ensure_infrastructure(self) -> bool:
        """确保nftables基础架构存在（表、链、跳转规则）"""
        try:
            # 1. 检查并创建filter表
            if not self._table_exists(self.filter_table_name):
                logger.info(f"创建 {self.filter_table_name} 表...")
                result = subprocess.run(
                    ['nft', 'add', 'table', 'inet', self.filter_table_name],
                    capture_output=True, text=True, shell=False
                )
                if result.returncode != 0:
                    logger.error(f"创建filter表失败: {result.stderr}")
                    return False
            
            # 2. 检查并创建input链
            if not self._chain_exists(self.filter_table_name, self.input_chain_name):
                logger.info(f"创建 {self.input_chain_name} 链...")
                result = subprocess.run(
                    ['nft', 'add', 'chain', 'inet', self.filter_table_name, self.input_chain_name, 
                     '{', 'type', 'filter', 'hook', 'input', 'priority', '0;', 'policy', 'accept;', '}'],
                    capture_output=True, text=True, shell=False
                )
                if result.returncode != 0:
                    logger.error(f"创建input链失败: {result.stderr}")
                    return False
            
            # 3. 检查并创建应用专用链
            if not self._chain_exists(self.filter_table_name, self.app_chain_name):
                logger.info(f"创建应用专用链 {self.app_chain_name}...")
                result = subprocess.run(
                    ['nft', 'add', 'chain', 'inet', self.filter_table_name, self.app_chain_name],
                    capture_output=True, text=True, shell=False
                )
                if result.returncode != 0:
                    logger.error(f"创建应用专用链失败: {result.stderr}")
                    return False
            
            # 4. 检查并添加跳转规则
            if not self._jump_rule_exists():
                logger.info(f"添加跳转规则到 {self.input_chain_name} 链...")
                # 获取当前input链中的规则数量，确定插入位置
                current_rules = self._get_chain_rule_count(self.filter_table_name, self.input_chain_name)
                insert_position = min(3, current_rules)  # 确保位置不超过现有规则数量
                
                result = subprocess.run(
                    ['nft', 'insert', 'rule', 'inet', self.filter_table_name, self.input_chain_name, 
                     'position', str(insert_position), 'jump', self.app_chain_name],
                    capture_output=True, text=True, shell=False
                )
                if result.returncode != 0:
                    logger.error(f"添加跳转规则失败: {result.stderr}")
                    return False
            
            logger.info("✅ nftables基础架构检查完成")
            return True
            
        except Exception as e:
            logger.error(f"确保基础架构时出错: {e}")
            return False
    
    def _table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            result = subprocess.run(
                ['nft', 'list', 'tables'],
                capture_output=True, text=True, shell=False
            )
            return table_name in result.stdout
        except Exception:
            return False
    
    def _chain_exists(self, table_name: str, chain_name: str) -> bool:
        """检查链是否存在"""
        try:
            result = subprocess.run(
                ['nft', 'list', 'chain', 'inet', table_name, chain_name],
                capture_output=True, text=True, shell=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _jump_rule_exists(self) -> bool:
        """检查跳转规则是否存在"""
        try:
            result = subprocess.run(
                ['nft', 'list', 'chain', 'inet', self.filter_table_name, self.input_chain_name],
                capture_output=True, text=True, shell=False
            )
            if result.returncode != 0:
                return False
            
            # 更精确的检查，确保是完整的跳转规则
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                # 检查是否包含跳转到YK_SAFE_CHAIN的规则
                if f"jump {self.app_chain_name}" in line:
                    return True
            
            return False
        except Exception:
            return False
    
    def _ensure_blacklist_infrastructure(self) -> bool:
        """确保黑名单基础架构存在（raw表、prerouting链、blacklist set）"""
        try:
            # 1. 检查并创建raw表
            if not self._table_exists(self.raw_table_name):
                logger.info(f"创建 {self.raw_table_name} 表...")
                result = subprocess.run(
                    ['nft', 'add', 'table', 'inet', self.raw_table_name],
                    capture_output=True, text=True, shell=False
                )
                if result.returncode != 0:
                    logger.error(f"创建raw表失败: {result.stderr}")
                    return False
            
            # 2. 检查并创建prerouting链
            if not self._chain_exists(self.raw_table_name, self.prerouting_chain_name):
                logger.info(f"创建 {self.prerouting_chain_name} 链...")
                result = subprocess.run(
                    ['nft', 'add', 'chain', 'inet', self.raw_table_name, self.prerouting_chain_name, 
                     '{', 'type', 'filter', 'hook', 'prerouting', 'priority', '-300;', 'policy', 'accept;', '}'],
                    capture_output=True, text=True, shell=False
                )
                if result.returncode != 0:
                    logger.error(f"创建prerouting链失败: {result.stderr}")
                    return False
            
            # 3. 检查并创建blacklist set
            if not self._set_exists(self.raw_table_name, 'blacklist'):
                logger.info("创建 blacklist set...")
                result = subprocess.run(
                    ['nft', 'add', 'set', 'inet', self.raw_table_name, 'blacklist', 
                     '{', 'type', 'ipv4_addr;', 'flags', 'interval;', 'auto-merge;', '}'],
                    capture_output=True, text=True, shell=False
                )
                if result.returncode != 0:
                    logger.error(f"创建blacklist set失败: {result.stderr}")
                    return False
            
            # 4. 检查并添加黑名单规则到prerouting链
            if not self._blacklist_rule_exists():
                logger.info("添加黑名单规则到prerouting链...")
                result = subprocess.run(
                    ['nft', 'add', 'rule', 'inet', self.raw_table_name, self.prerouting_chain_name, 
                     'ip', 'saddr', '@blacklist', 'drop'],
                    capture_output=True, text=True, shell=False
                )
                if result.returncode != 0:
                    logger.error(f"添加黑名单规则失败: {result.stderr}")
                    return False
            
            logger.info("✅ 黑名单基础架构检查完成")
            return True
            
        except Exception as e:
            logger.error(f"确保黑名单基础架构时出错: {e}")
            return False
    
    def _set_exists(self, table_name: str, set_name: str) -> bool:
        """检查set是否存在"""
        try:
            result = subprocess.run(
                ['nft', 'list', 'set', 'inet', table_name, set_name],
                capture_output=True, text=True, shell=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _blacklist_rule_exists(self) -> bool:
        """检查黑名单规则是否存在"""
        try:
            result = subprocess.run(
                ['nft', 'list', 'chain', 'inet', self.raw_table_name, self.prerouting_chain_name],
                capture_output=True, text=True, shell=False
            )
            return 'ip saddr @blacklist drop' in result.stdout
        except Exception:
            return False
    
    def _get_chain_rule_count(self, table_name: str, chain_name: str) -> int:
        """获取链中的规则数量"""
        try:
            result = subprocess.run(
                ['nft', 'list', 'chain', 'inet', table_name, chain_name],
                capture_output=True, text=True, shell=False
            )
            if result.returncode != 0:
                return 0
            
            # 计算实际规则行数（排除注释和空行）
            lines = result.stdout.strip().split('\n')
            rule_count = 0
            for line in lines:
                line = line.strip()
                # 跳过注释、空行、链定义行
                if (line and not line.startswith('#') and 
                    not line.startswith('chain') and 
                    not line.startswith('type') and 
                    not line.startswith('policy') and
                    not line.startswith('}')):
                    rule_count += 1
            
            return rule_count
        except Exception:
            return 0

    def sync_rules_from_db(self) -> bool:
        """
        从数据库同步所有规则到应用专用链
        替代原来的 apply_config 方法，不再使用 flush ruleset
        """
        try:
            # 确保基础架构存在
            if not self._ensure_infrastructure():
                logger.error("无法确保基础架构存在，跳过规则同步")
                return False
            
            # 1. 清空现有应用规则
            logger.info(f"正在清空应用专用链 {self.app_chain_name} 中的所有规则...")
            flush_result = subprocess.run(
                ['nft', 'flush', 'chain', 'inet', self.filter_table_name, self.app_chain_name],
                capture_output=True, text=True, shell=False
            )
            
            if flush_result.returncode != 0:
                logger.error(f"清空应用专用链失败: {flush_result.stderr}")
                return False
            
            # 2. 从数据库获取所有活动规则
            rules = self.db.query(FirewallRule).filter(FirewallRule.is_active == True).all()
            logger.info(f"从数据库获取到 {len(rules)} 条活动规则")
            
            # 3. 逐条将规则添加到应用专用链中
            success_count = 0
            for rule in rules:
                if self.add_rule_realtime(rule):
                    success_count += 1
                else:
                    logger.error(f"添加规则失败: {rule.rule_name}")
            
            logger.info(f"✅ 规则同步完成: {success_count}/{len(rules)} 条规则成功添加")
            return success_count == len(rules)
            
        except Exception as e:
            logger.error(f"同步规则时出错: {e}")
            return False

    # ==================== 连接状态管理 ====================
    
    def _terminate_active_connections(self, ip_address: str) -> bool:
        """
        使用 ss 和 conntrack 主动终止并清理指定IP的所有活跃连接。
        
        步骤1: 使用 ss -K 主动发送TCP RST包 (立即踢下线)
        步骤2: 使用 conntrack -D 清理防火墙状态表 (确保状态纯净)
        """
        logger.info(f"正在主动终止并清理IP {ip_address} 的所有活跃连接...")
        
        success_ss = False
        success_conntrack = False

        # 步骤 1: 使用 ss -K 主动发送TCP RST包 (立即踢下线)
        ss_command = ['ss', '-K', 'src', ip_address]
        try:
            logger.info(f"执行 ss -K 命令: {' '.join(ss_command)}")
            result_ss = subprocess.run(ss_command, capture_output=True, text=True, shell=False)
            # ss -K 即使找不到连接也会成功返回0，所以我们主要关心是否有错误
            if result_ss.returncode == 0:
                logger.info(f"✅ ss -K 命令成功执行，已向IP {ip_address} 的连接发送终止信号")
                success_ss = True
            else:
                # 如果ss命令本身出错（比如在某些极简系统上不存在）
                logger.error(f"❌ 执行 ss -K 命令失败: {result_ss.stderr.strip()}")
        except FileNotFoundError:
            logger.warning("⚠️ `ss` 命令未找到，跳过主动连接终止。建议安装 `iproute2` 包。")
        except Exception as e:
            logger.error(f"❌ 执行 ss -K 命令时出现异常: {e}")

        # 步骤 2: 使用 conntrack -D 清理防火墙状态表 (确保状态纯净)
        conntrack_command = ['conntrack', '-D', '-s', ip_address]
        try:
            logger.info(f"执行 conntrack -D 命令: {' '.join(conntrack_command)}")
            result_ct = subprocess.run(conntrack_command, capture_output=True, text=True, shell=False)
            if result_ct.returncode == 0:
                logger.info(f"✅ conntrack -D 命令成功执行，已清除IP {ip_address} 的连接状态")
                success_conntrack = True
            else:
                logger.error(f"❌ 执行 conntrack -D 命令失败: {result_ct.stderr.strip()}")
        except FileNotFoundError:
            logger.warning("⚠️ `conntrack` 命令未找到，跳过状态清理。建议安装 `conntrack-tools`。")
            # 即使 conntrack 失败，如果 ss 成功了，我们也可以认为主要目标达成了
            success_conntrack = True 
        except Exception as e:
            logger.error(f"❌ 执行 conntrack -D 命令时出现异常: {e}")

        # 评估结果
        if success_ss and success_conntrack:
            logger.info(f"🎉 IP {ip_address} 的连接终止和状态清理都成功完成")
            return True
        elif success_ss:
            logger.info(f"✅ IP {ip_address} 的连接已主动终止，但状态清理可能不完整")
            return True
        elif success_conntrack:
            logger.warning(f"⚠️ IP {ip_address} 的状态已清理，但主动终止可能失败")
            return True
        else:
            logger.error(f"❌ IP {ip_address} 的连接终止和状态清理都失败")
            logger.info("IP已被添加到黑名单，新连接将被拦截，但现有连接可能需要时间自然断开")
            return False
    
    def add_ip_to_blacklist_realtime(self, ip_address: str, description: str = None) -> bool:
        """
        实时将IP添加到黑名单 - 立即生效并踢下线
        
        逻辑流程：
        1. 将IP写入数据库
        2. 实时将IP添加到nftables的set中 (拦截新连接)
        3. 调用 _terminate_active_connections 清除现有连接 (踢下线)
        """
        try:
            logger.info(f"开始将IP {ip_address} 添加到黑名单...")
            
            # 1. 将IP写入数据库
            from app.db.models import BlacklistIP
            blacklist_ip = BlacklistIP(
                ip_address=ip_address,
                description=description or f"实时添加 - {ip_address}",
                is_active=True
            )
            self.db.add(blacklist_ip)
            self.db.commit()
            self.db.refresh(blacklist_ip)
            
            logger.info(f"✅ IP {ip_address} 已写入数据库")
            
            # 2. 确保raw表和黑名单set存在
            if not self._ensure_blacklist_infrastructure():
                logger.error("无法确保黑名单基础架构存在")
                self.db.rollback()
                return False
            
            # 3. 实时将IP添加到nftables的set中 (拦截新连接)
            nft_command = [
                'nft', 'add', 'element', 'inet', self.raw_table_name, 
                'blacklist', '{', ip_address, '}'
            ]
            
            logger.info(f"执行添加IP到黑名单命令: {' '.join(nft_command)}")
            
            result = subprocess.run(nft_command, capture_output=True, text=True, shell=False)
            
            if result.returncode != 0:
                logger.error(f"添加IP到黑名单失败: {result.stderr}")
                # 回滚数据库操作
                self.db.rollback()
                return False
            
            logger.info(f"✅ IP {ip_address} 已添加到nftables黑名单set")
            
            # 4. 调用 _terminate_active_connections 清除现有连接 (踢下线)
            if self._terminate_active_connections(ip_address):
                logger.info(f"✅ IP {ip_address} 的所有活跃连接已被终止")
            else:
                logger.warning(f"⚠️ IP {ip_address} 的连接终止可能失败，但IP已被添加到黑名单")
            
            logger.info(f"🎉 IP {ip_address} 已成功添加到黑名单并踢下线")
            logger.info("⏰ 提示：规则变更将在30秒后完全生效，请耐心等待")
            return True
            
        except Exception as e:
            logger.error(f"添加IP到黑名单时出错: {e}")
            # 回滚数据库操作
            try:
                self.db.rollback()
            except:
                pass
            return False
    
    def remove_ip_from_blacklist_realtime(self, ip_address: str) -> bool:
        """
        实时将IP从黑名单移除 - 立即生效
        
        逻辑流程：
        1. 从数据库中移除IP
        2. 实时从nftables的set中移除IP
        """
        try:
            logger.info(f"开始将IP {ip_address} 从黑名单移除...")
            
            # 1. 从数据库中移除IP
            from app.db.models import BlacklistIP
            blacklist_ip = self.db.query(BlacklistIP).filter(
                BlacklistIP.ip_address == ip_address,
                BlacklistIP.is_active == True
            ).first()
            
            if blacklist_ip:
                blacklist_ip.is_active = False
                self.db.commit()
                logger.info(f"✅ IP {ip_address} 已从数据库移除")
            else:
                logger.warning(f"⚠️ IP {ip_address} 在数据库中未找到或已非活跃状态")
            
            # 2. 确保黑名单基础架构存在
            if not self._ensure_blacklist_infrastructure():
                logger.error("无法确保黑名单基础架构存在")
                return False
            
            # 3. 实时从nftables的set中移除IP
            nft_command = [
                'nft', 'delete', 'element', 'inet', self.raw_table_name, 
                'blacklist', '{', ip_address, '}'
            ]
            
            logger.info(f"执行从黑名单移除IP命令: {' '.join(nft_command)}")
            
            result = subprocess.run(nft_command, capture_output=True, text=True, shell=False)
            
            if result.returncode != 0:
                logger.error(f"从黑名单移除IP失败: {result.stderr}")
                return False
            
            logger.info(f"✅ IP {ip_address} 已从nftables黑名单set移除")
            logger.info(f"🎉 IP {ip_address} 已成功从黑名单移除")
            logger.info("⏰ 提示：规则变更将在30秒后完全生效，请耐心等待")
            return True
            
        except Exception as e:
            logger.error(f"从黑名单移除IP时出错: {e}")
            return False
    
    def get_active_connections(self, ip_address: str = None) -> List[Dict[str, Any]]:
        """
        获取活跃连接信息
        
        Args:
            ip_address: 可选，指定IP地址。如果不指定，则获取所有活跃连接
            
        Returns:
            连接信息列表
        """
        try:
            # 检查 conntrack 命令是否存在
            try:
                subprocess.run(['conntrack', '-h'], capture_output=True, check=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                logger.warning("`conntrack` 命令未找到或无法执行。连接状态管理功能不可用。")
                return []

            # 构建命令
            if ip_address:
                command = ['conntrack', '-L', '-s', ip_address]
            else:
                command = ['conntrack', '-L']
            
            result = subprocess.run(command, capture_output=True, text=True, shell=False)
            
            if result.returncode != 0:
                logger.error(f"获取连接信息失败: {result.stderr}")
                return []
            
            # 解析连接信息
            connections = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # 解析连接行，格式类似：
                    # tcp 6 431999 ESTABLISHED src=192.168.1.100 dst=8.8.8.8 sport=12345 dport=53 packets=1 bytes=52 src=8.8.8.8 dst=192.168.1.100 sport=53 dport=12345 packets=1 bytes=52 mark=0 use=1
                    try:
                        parts = line.split()
                        if len(parts) >= 4:
                            connection_info = {
                                'protocol': parts[0],
                                'state': parts[3],
                                'raw_line': line
                            }
                            
                            # 提取源IP和目标IP
                            for part in parts:
                                if part.startswith('src='):
                                    connection_info['source_ip'] = part.split('=')[1]
                                elif part.startswith('dst='):
                                    connection_info['destination_ip'] = part.split('=')[1]
                                elif part.startswith('sport='):
                                    connection_info['source_port'] = part.split('=')[1]
                                elif part.startswith('dport='):
                                    connection_info['destination_port'] = part.split('=')[1]
                            
                            connections.append(connection_info)
                    except Exception as e:
                        logger.warning(f"解析连接行时出错: {line}, 错误: {e}")
                        continue
            
            logger.info(f"获取到 {len(connections)} 个活跃连接")
            return connections
            
        except Exception as e:
            logger.error(f"获取活跃连接时出错: {e}")
            return []
    

    


