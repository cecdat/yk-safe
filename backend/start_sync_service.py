#!/usr/bin/env python3
"""
启动nftables同步服务
"""

import sys
import os
import signal
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.nftables_sync_service import start_sync_service, stop_sync_service, get_sync_status

def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n收到信号 {signum}，正在停止服务...")
    stop_sync_service()
    sys.exit(0)

def main():
    """主函数"""
    print("🚀 启动nftables同步服务...")
    print("=" * 50)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动同步服务
        start_sync_service()
        
        print("✅ 同步服务已启动")
        print("📋 服务信息:")
        
        # 显示服务状态
        while True:
            status = get_sync_status()
            print(f"   状态: {'运行中' if status['is_running'] else '已停止'}")
            print(f"   同步间隔: {status['sync_interval']} 秒")
            print(f"   同步次数: {status['sync_count']}")
            print(f"   最后同步: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['last_sync_time'])) if status['last_sync_time'] > 0 else '从未同步'}")
            print(f"   运行时间: {status['uptime']:.0f} 秒")
            print("-" * 30)
            
            # 每30秒更新一次状态
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止服务...")
    except Exception as e:
        print(f"服务运行出错: {e}")
    finally:
        stop_sync_service()
        print("服务已停止")

if __name__ == "__main__":
    main()
