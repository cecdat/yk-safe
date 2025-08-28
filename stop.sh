#!/bin/bash

# YK-Safe 停止服务脚本

echo "🛑 停止 YK-Safe 服务..."

# 停止后端服务
echo "停止后端服务..."
systemctl stop yk-safe-backend 2>/dev/null || echo "后端服务未运行"

# 停止nginx服务
echo "停止nginx服务..."
systemctl stop nginx 2>/dev/null || echo "nginx服务未运行"

# 禁用服务
echo "禁用服务..."
systemctl disable yk-safe-backend 2>/dev/null || echo "后端服务未配置"
systemctl disable nginx 2>/dev/null || echo "nginx服务未配置"

echo "✅ 所有服务已停止"
echo ""
echo "📝 如需完全卸载，请运行："
echo "   rm -rf /opt/yk-safe"
echo "   rm -f /etc/systemd/system/yk-safe-backend.service"
