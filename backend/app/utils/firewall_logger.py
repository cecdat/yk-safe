#!/usr/bin/env python3
"""
防火墙日志记录工具
用于记录防火墙事件，包括连接尝试、规则匹配等
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import FirewallLog, FirewallRule
from app.utils.geo_utils import get_ip_location_simple
import asyncio
import threading
from queue import Queue
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirewallLogger:
    """防火墙日志记录器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.log_queue = Queue(maxsize=10000)  # 日志队列
        self.is_running = False
        self.worker_thread = None
        
    def start_worker(self):
        """启动日志处理工作线程"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._process_logs, daemon=True)
            self.worker_thread.start()
            logger.info("防火墙日志记录器工作线程已启动")
    
    def stop_worker(self):
        """停止日志处理工作线程"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
            logger.info("防火墙日志记录器工作线程已停止")
    
    def _process_logs(self):
        """处理日志队列的工作线程"""
        while self.is_running:
            try:
                # 批量处理日志，提高性能
                logs_to_process = []
                for _ in range(100):  # 最多处理100条日志
                    try:
                        log_data = self.log_queue.get_nowait()
                        logs_to_process.append(log_data)
                    except:
                        break
                
                if logs_to_process:
                    self._batch_insert_logs(logs_to_process)
                
                # 短暂休眠，避免CPU占用过高
                asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"处理防火墙日志时出错: {e}")
                asyncio.sleep(1)
    
    def _batch_insert_logs(self, logs_data: list):
        """批量插入日志到数据库"""
        try:
            logs = []
            for log_data in logs_data:
                log = FirewallLog(**log_data)
                logs.append(log)
            
            self.db.add_all(logs)
            self.db.commit()
            logger.debug(f"批量插入 {len(logs)} 条防火墙日志")
            
        except Exception as e:
            logger.error(f"批量插入防火墙日志失败: {e}")
            self.db.rollback()
    
    def log_connection_attempt(
        self,
        source_ip: str,
        destination_ip: str,
        protocol: str,
        source_port: Optional[int] = None,
        destination_port: Optional[int] = None,
        action: str = "drop",
        rule_id: Optional[int] = None,
        rule_name: Optional[str] = None,
        interface: Optional[str] = None,
        packet_size: Optional[int] = None,
        tcp_flags: Optional[str] = None,
        description: Optional[str] = None
    ):
        """记录连接尝试"""
        try:
            # 异步获取地理位置信息
            geo_info = self._get_ip_location_async(source_ip)
            
            # 确定威胁等级
            threat_level = self._determine_threat_level(
                source_ip, action, protocol, destination_port
            )
            
            log_data = {
                "source_ip": source_ip,
                "destination_ip": destination_ip,
                "protocol": protocol,
                "source_port": source_port,
                "destination_port": destination_port,
                "action": action,
                "rule_id": rule_id,
                "rule_name": rule_name,
                "interface": interface,
                "packet_size": packet_size,
                "tcp_flags": tcp_flags,
                "country": geo_info.get("country") if geo_info else None,
                "city": geo_info.get("city") if geo_info else None,
                "isp": geo_info.get("isp") if geo_info else None,
                "threat_level": threat_level,
                "description": description,
                "timestamp": datetime.utcnow()
            }
            
            # 将日志添加到队列
            try:
                self.log_queue.put_nowait(log_data)
            except:
                logger.warning("防火墙日志队列已满，丢弃日志")
                
        except Exception as e:
            logger.error(f"记录防火墙日志失败: {e}")
    
    def _get_ip_location_async(self, ip: str) -> Optional[Dict[str, Any]]:
        """异步获取IP地理位置信息"""
        try:
            # 跳过本地IP和私有IP
            if ip in ['127.0.0.1', 'localhost', '::1'] or ip.startswith(('192.168.', '10.', '172.')):
                return {
                    "country": "本地",
                    "city": "本地网络",
                    "isp": "本地"
                }
            
            # 获取地理位置信息
            geo_info = get_ip_location_simple(ip)
            return geo_info
            
        except Exception as e:
            logger.debug(f"获取IP {ip} 地理位置信息失败: {e}")
            return None
    
    def _determine_threat_level(
        self, 
        source_ip: str, 
        action: str, 
        protocol: str, 
        destination_port: Optional[int]
    ) -> str:
        """确定威胁等级"""
        # 默认威胁等级
        threat_level = "low"
        
        # 根据动作调整威胁等级
        if action == "drop":
            threat_level = "medium"
        elif action == "reject":
            threat_level = "high"
        
        # 根据目标端口调整威胁等级
        if destination_port:
            # 常见攻击端口
            high_risk_ports = [22, 23, 3389, 1433, 3306, 5432, 6379, 27017]
            if destination_port in high_risk_ports:
                threat_level = "high"
            
            # 管理端口
            admin_ports = [22, 23, 3389, 5900, 8080, 8443]
            if destination_port in admin_ports:
                threat_level = "critical"
        
        # 根据协议调整威胁等级
        if protocol == "icmp":
            threat_level = "medium"  # ICMP可能用于扫描
        
        return threat_level
    
    def log_rule_match(
        self,
        rule: FirewallRule,
        source_ip: str,
        destination_ip: str,
        protocol: str,
        action: str,
        **kwargs
    ):
        """记录规则匹配"""
        self.log_connection_attempt(
            source_ip=source_ip,
            destination_ip=destination_ip,
            protocol=protocol,
            action=action,
            rule_id=rule.id,
            rule_name=rule.rule_name,
            description=f"规则匹配: {rule.description or rule.rule_name}",
            **kwargs
        )
    
    def log_blacklist_block(
        self,
        source_ip: str,
        destination_ip: str,
        protocol: str,
        **kwargs
    ):
        """记录黑名单阻止"""
        self.log_connection_attempt(
            source_ip=source_ip,
            destination_ip=destination_ip,
            protocol=protocol,
            action="drop",
            description="黑名单IP阻止",
            threat_level="high",
            **kwargs
        )
    
    def log_whitelist_allow(
        self,
        source_ip: str,
        destination_ip: str,
        protocol: str,
        **kwargs
    ):
        """记录白名单允许"""
        self.log_connection_attempt(
            source_ip=source_ip,
            destination_ip=destination_ip,
            protocol=protocol,
            action="accept",
            description="白名单IP允许",
            threat_level="low",
            **kwargs
        )
    
    def get_log_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取日志摘要统计"""
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # 统计各种动作的日志数量
            action_stats = self.db.query(
                FirewallLog.action,
                self.db.func.count(FirewallLog.id).label('count')
            ).filter(
                FirewallLog.timestamp >= cutoff_time
            ).group_by(FirewallLog.action).all()
            
            # 统计威胁等级分布
            threat_stats = self.db.query(
                FirewallLog.threat_level,
                self.db.func.count(FirewallLog.id).label('count')
            ).filter(
                FirewallLog.timestamp >= cutoff_time
            ).group_by(FirewallLog.threat_level).all()
            
            # 统计协议分布
            protocol_stats = self.db.query(
                FirewallLog.protocol,
                self.db.func.count(FirewallLog.id).label('count')
            ).filter(
                FirewallLog.timestamp >= cutoff_time
            ).group_by(FirewallLog.protocol).all()
            
            # 统计源IP分布（前10个）
            top_source_ips = self.db.query(
                FirewallLog.source_ip,
                self.db.func.count(FirewallLog.id).label('count')
            ).filter(
                FirewallLog.timestamp >= cutoff_time
            ).group_by(FirewallLog.source_ip).order_by(
                self.db.func.count(FirewallLog.id).desc()
            ).limit(10).all()
            
            return {
                "action_stats": {stat.action: stat.count for stat in action_stats},
                "threat_stats": {stat.threat_level: stat.count for stat in threat_stats},
                "protocol_stats": {stat.protocol: stat.count for stat in protocol_stats},
                "top_source_ips": [{"ip": stat.source_ip, "count": stat.count} for stat in top_source_ips],
                "total_logs": sum(stat.count for stat in action_stats),
                "time_range": f"最近{hours}小时"
            }
            
        except Exception as e:
            logger.error(f"获取日志摘要失败: {e}")
            return {}
    
    def cleanup_old_logs(self, days: int = 30):
        """清理旧日志"""
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = self.db.query(FirewallLog).filter(
                FirewallLog.timestamp < cutoff_time
            ).delete()
            
            self.db.commit()
            logger.info(f"清理了 {deleted_count} 条旧防火墙日志（{days}天前）")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
            self.db.rollback()
            return 0
