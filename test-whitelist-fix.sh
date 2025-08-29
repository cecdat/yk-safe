#!/bin/bash

# 白名单模式规则顺序修复测试脚本
# 用于验证新增的白名单IP是否能正常访问

echo "🔍 开始测试白名单模式规则顺序修复..."

# 1. 检查当前防火墙状态
echo "📊 检查当前防火墙状态..."
nft list chain inet filter YK_SAFE_CHAIN

echo ""
echo "🔧 测试步骤："
echo "1. 确保防火墙处于白名单模式"
echo "2. 添加一个新的白名单IP"
echo "3. 检查规则顺序是否正确（accept规则在drop规则之前）"
echo "4. 测试新IP是否能正常访问"

echo ""
echo "⚠️  请手动执行以下操作来验证修复："
echo ""
echo "1. 在管理界面添加一个新的白名单IP"
echo "2. 运行命令检查规则顺序："
echo "   nft list chain inet filter YK_SAFE_CHAIN"
echo ""
echo "3. 验证规则顺序应该是："
echo "   - 预设IP规则 (accept)"
echo "   - 用户自定义accept规则"
echo "   - drop规则"
echo "   - 用户自定义drop规则（如果有）"
echo ""
echo "4. 测试新IP是否能正常访问服务器"

echo ""
echo "✅ 如果规则顺序正确且新IP能正常访问，说明修复成功！"

# 5. 提供验证命令
echo ""
echo "🔍 验证命令："
echo "# 查看当前规则顺序"
echo "nft list chain inet filter YK_SAFE_CHAIN"
echo ""
echo "# 测试新IP连接（替换为实际IP）"
echo "ping -c 3 新IP地址"
echo ""
echo "# 检查防火墙日志"
echo "tail -f /var/log/nftables.log"
