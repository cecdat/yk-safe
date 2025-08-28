#!/usr/bin/env python3
"""
nftables同步服务 - 定时将实时规则同步到持久化配置文件
"""

import time
import threading
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.utils.nftables_generator import NftablesGenerator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NftablesSyncService:
    """nftables同步服务"""
    
    def __init__(self, sync_interval: int = 300):  # 默认5分钟同步一次
        self.sync_interval = sync_interval
        self.is_running = False
        self.sync_thread: Optional[threading.Thread] = None
        self.last_sync_time = 0
        self.sync_count = 0
        
    def start(self):
        """启动同步服务"""
        if self.is_running:
            logger.warning("同步服务已在运行中")
            return
        
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("nftables同步服务已启动")
    
    def stop(self):
        """停止同步服务"""
        if not self.is_running:
            logger.warning("同步服务未在运行")
            return
        
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        logger.info("nftables同步服务已停止")
    
    def _sync_loop(self):
        """同步循环"""
        while self.is_running:
            try:
                # 执行同步
                self._perform_sync()
                
                # 等待下次同步
                time.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"同步过程中出错: {e}")
                # 出错后等待较短时间再重试
                time.sleep(60)
    
    def _perform_sync(self):
        """执行同步操作"""
        try:
            db = SessionLocal()
            generator = NftablesGenerator(db)
            
            # 检查是否需要同步
            if not self._needs_sync(generator):
                logger.debug("无需同步，跳过本次同步")
                return
            
            # 执行同步
            if generator.sync_to_persistent():
                self.last_sync_time = time.time()
                self.sync_count += 1
                logger.info(f"同步成功，已同步 {self.sync_count} 次")
            else:
                logger.error("同步失败")
                
        except Exception as e:
            logger.error(f"执行同步时出错: {e}")
        finally:
            if 'db' in locals():
                db.close()
    
    def _needs_sync(self, generator: NftablesGenerator) -> bool:
        """检查是否需要同步"""
        try:
            # 获取当前实时规则
            realtime_rules = generator.list_rules_realtime()
            
            # 获取配置文件中的规则数量
            config_content = generator.generate_config()
            config_lines = config_content.split('\n')
            
            # 统计配置文件中的规则数量
            config_rule_count = 0
            for line in config_lines:
                if 'ip saddr' in line and ('drop' in line or 'accept' in line):
                    config_rule_count += 1
            
            # 统计实时规则数量（排除系统规则）
            realtime_rule_count = 0
            for rule in realtime_rules:
                if 'ip saddr' in rule and ('drop' in rule or 'accept' in line):
                    realtime_rule_count += 1
            
            # 如果数量不匹配，需要同步
            if realtime_rule_count != config_rule_count:
                logger.info(f"规则数量不匹配: 实时={realtime_rule_count}, 配置={config_rule_count}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查同步需求时出错: {e}")
            # 出错时默认需要同步
            return True
    
    def force_sync(self) -> bool:
        """强制同步"""
        try:
            db = SessionLocal()
            generator = NftablesGenerator(db)
            
            if generator.sync_to_persistent():
                self.last_sync_time = time.time()
                self.sync_count += 1
                logger.info("强制同步成功")
                return True
            else:
                logger.error("强制同步失败")
                return False
                
        except Exception as e:
            logger.error(f"强制同步时出错: {e}")
            return False
        finally:
            if 'db' in locals():
                db.close()
    
    def get_status(self) -> dict:
        """获取服务状态"""
        return {
            'is_running': self.is_running,
            'sync_interval': self.sync_interval,
            'last_sync_time': self.last_sync_time,
            'sync_count': self.sync_count,
            'uptime': time.time() - self.last_sync_time if self.last_sync_time > 0 else 0
        }
    
    def set_sync_interval(self, interval: int):
        """设置同步间隔"""
        if interval < 60:  # 最小1分钟
            interval = 60
        self.sync_interval = interval
        logger.info(f"同步间隔已设置为 {interval} 秒")

# 全局同步服务实例
_sync_service: Optional[NftablesSyncService] = None

def get_sync_service() -> NftablesSyncService:
    """获取同步服务实例"""
    global _sync_service
    if _sync_service is None:
        _sync_service = NftablesSyncService()
    return _sync_service

def start_sync_service():
    """启动同步服务"""
    service = get_sync_service()
    service.start()

def stop_sync_service():
    """停止同步服务"""
    service = get_sync_service()
    service.stop()

def force_sync():
    """强制同步"""
    service = get_sync_service()
    return service.force_sync()

def get_sync_status():
    """获取同步状态"""
    service = get_sync_service()
    return service.get_status()

if __name__ == "__main__":
    # 测试代码
    service = NftablesSyncService(sync_interval=60)  # 1分钟同步一次
    
    try:
        service.start()
        time.sleep(120)  # 运行2分钟
    except KeyboardInterrupt:
        print("收到中断信号，正在停止服务...")
    finally:
        service.stop()
        print("服务已停止")
