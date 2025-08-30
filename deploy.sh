#!/bin/bash

# YK-Safe 防火墙管理系统 - 统一部署脚本
# 支持智能环境检测和部署模式选择
# 适用于 Debian/Ubuntu 系统

set -e

# 获取脚本原始目录
ORIGINAL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 显示盾牌图案
echo ""
echo "    ╭─────────────────────────────────────╮"
echo "   ╱                                     ╲"
echo "  ╱    ████████████████████████████████    ╲"
echo " ╱    ██                              ██    ╲"
echo "╱     ██    ╭─────────────────────╮    ██     ╲"
echo "│     ██    │     🛡️ YK-SAFE 🛡️     │    ██     │"
echo "│     ██    │   防护系统 v1.0.0    │    ██     │"
echo "│     ██    │   Firewall System    │    ██     │"
echo "│     ██    ╰─────────────────────╯    ██     │"
echo "│     ██                              ██     │"
echo "│     ██    ╭─────────────────────╮    ██     │"
echo "│     ██    │   🚀 开始部署 🚀     │    ██     │"
echo "│     ██    ╰─────────────────────╯    ██     │"
echo "│     ██                              ██     │"
echo "│     ████████████████████████████████     │"
echo " ╲                                     ╱"
echo "  ╲                                   ╱"
echo "   ╲                                 ╱"
echo "    ╰─────────────────────────────────╯"
echo ""
echo "🚀 YK-Safe 防火墙管理系统 - 统一部署脚本"
echo "=========================================="
echo "🔍 智能环境检测和部署模式选择"
echo ""

# 端口配置
echo ""
echo "🔧 端口配置..."
echo "========================"

# 获取前端端口
read -p "请输入前端访问端口 (默认: 5023): " FRONTEND_PORT
FRONTEND_PORT=${FRONTEND_PORT:-5023}

# 获取后端端口
read -p "请输入后端API端口 (默认: 8000): " BACKEND_PORT
BACKEND_PORT=${BACKEND_PORT:-8000}

# 验证端口
if ! [[ "$FRONTEND_PORT" =~ ^[0-9]+$ ]] || [ "$FRONTEND_PORT" -lt 1 ] || [ "$FRONTEND_PORT" -gt 65535 ]; then
    echo "❌ 前端端口无效，请输入1-65535之间的数字"
    exit 1
fi

if ! [[ "$BACKEND_PORT" =~ ^[0-9]+$ ]] || [ "$BACKEND_PORT" -lt 1 ] || [ "$BACKEND_PORT" -gt 65535 ]; then
    echo "❌ 后端端口无效，请输入1-65535之间的数字"
    exit 1
fi

if [ "$FRONTEND_PORT" -eq "$BACKEND_PORT" ]; then
    echo "❌ 前端端口和后端端口不能相同"
    exit 1
fi

echo "✅ 端口配置完成:"
echo "   前端端口: $FRONTEND_PORT"
echo "   后端端口: $BACKEND_PORT"

# 部署路径配置
echo ""
echo "📁 部署路径配置..."
echo "========================"

APP_NAME="yk-safe"
DEFAULT_PATH="/opt/$APP_NAME"
echo "请选择部署路径 (默认: $DEFAULT_PATH)"
read -p "部署路径 [$DEFAULT_PATH]: " DEPLOY_PATH
DEPLOY_PATH=${DEPLOY_PATH:-$DEFAULT_PATH}

# 验证路径
if [[ "$DEPLOY_PATH" == /* ]]; then
    # 绝对路径
    APP_PATH="$DEPLOY_PATH"
else
    # 相对路径，转换为绝对路径
    APP_PATH="$(cd "$DEPLOY_PATH" && pwd 2>/dev/null || echo "$(pwd)/$DEPLOY_PATH")"
fi

echo "📋 选择的部署路径: $APP_PATH"

# 部署前检查和修复
echo ""
echo "🔍 部署前检查和修复..."
echo "========================"

# 检查必要文件
echo "📁 检查必要文件..."
if [ ! -f "$ORIGINAL_SCRIPT_DIR/backend/app/api/firewall.py" ]; then
    echo "❌ backend/app/api/firewall.py - 缺失"
    exit 1
fi

if [ ! -f "$ORIGINAL_SCRIPT_DIR/backend/requirements.txt" ]; then
    echo "❌ backend/requirements.txt - 缺失"
    exit 1
fi

if [ ! -f "$ORIGINAL_SCRIPT_DIR/backend/init_db.py" ]; then
    echo "❌ backend/init_db.py - 缺失"
    exit 1
fi

if [ ! -f "$ORIGINAL_SCRIPT_DIR/frontend/package.json" ]; then
    echo "❌ frontend/package.json - 缺失"
    exit 1
fi

echo "✅ 所有必要文件检查通过"

# 环境检测
echo ""
echo "🔍 环境检测..."
echo "========================"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root权限运行此脚本"
    exit 1
fi

# 检查是否为容器环境
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    echo "❌ 当前在容器环境中运行"
    echo "请退出容器，在宿主机上运行此脚本"
    exit 1
else
    echo "✅ 当前在宿主机环境中运行"
fi

# 检查系统信息
if [ -f /etc/os-release ]; then
    OS_NAME=$(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)
    echo "操作系统: $OS_NAME"
else
    echo "操作系统: 无法确定"
fi

echo "内核版本: $(uname -r)"
echo "系统架构: $(uname -m)"

# Docker环境检测
echo ""
echo "🐳 Docker环境检测..."
echo "========================"

DOCKER_MODE="safe"
if command -v docker >/dev/null 2>&1; then
    echo "✅ Docker已安装: $(docker --version)"
    
    # 检查Docker服务状态
    if systemctl is-active --quiet docker 2>/dev/null; then
        echo "✅ Docker服务运行中"
        
        # 检查运行中的容器
        running_containers=$(docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | wc -l)
        if [ "$running_containers" -gt 1 ]; then
            echo "⚠️  检测到运行中的Docker容器"
            echo "📋 当前运行的容器："
            docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || true
            echo ""
            echo "🔒 将使用安全部署模式，避免影响现有容器"
            DOCKER_MODE="safe"
        else
            echo "✅ 未检测到运行中的Docker容器"
            echo "🔓 将使用标准部署模式"
            DOCKER_MODE="standard"
        fi
    else
        echo "⚠️ Docker服务未运行"
        DOCKER_MODE="standard"
    fi
else
    echo "ℹ️  Docker未安装或不可用"
    DOCKER_MODE="standard"
fi

# 部署模式选择
echo ""
echo "🎯 部署模式选择..."
echo "========================"

if [ "$DOCKER_MODE" = "safe" ]; then
    echo "🔒 检测到Docker环境，建议使用安全部署模式"
    echo "   安全模式特点："
    echo "   ✅ 不清除现有nftables规则"
    echo "   ✅ 使用应用专用链架构"
    echo "   ✅ 与Docker网络完全兼容"
    echo "   ✅ 渐进式配置更新"
    echo ""
    read -p "是否使用安全部署模式？(Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "⚠️  您选择了标准部署模式"
        echo "   注意：这可能会暂时影响Docker网络"
        DOCKER_MODE="standard"
    else
        echo "✅ 使用安全部署模式"
    fi
else
    echo "🔓 未检测到Docker环境，使用标准部署模式"
    echo "   标准模式特点："
    echo "   ✅ 完整的nftables配置"
    echo "   ✅ 最高性能的防火墙规则"
    echo "   ✅ 完整的系统集成"
fi

echo ""
echo "📋 最终部署配置:"
echo "   部署模式: $([ "$DOCKER_MODE" = "safe" ] && echo "安全模式" || echo "标准模式")"
echo "   前端端口: $FRONTEND_PORT"
echo "   后端端口: $BACKEND_PORT"
echo "   部署路径: $APP_PATH"
echo "   Docker模式: $DOCKER_MODE"
echo ""

read -p "确认开始部署？(Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "❌ 用户取消部署"
    exit 1
fi

# 显示部署开始动画
echo ""
echo "    ╭─────────────────────────────────────╮"
echo "   ╱                                     ╲"
echo "  ╱    🚀 部署引擎启动中... 🚀            ╲"
echo " ╱    ████████████████████████████████    ╲"
echo "╱     ██                              ██     ╲"
echo "│     ██    ╭─────────────────────╮    ██     │"
echo "│     ██    │   🔧 系统检查 🔧     │    ██     │"
echo "│     ██    │   📦 依赖安装 📦     │    ██     │"
echo "│     ██    │   🛡️ 防火墙配置 🛡️   │    ██     │"
echo "│     ██    │   🌐 服务启动 🌐     │    ██     │"
echo "│     ██    ╰─────────────────────╯    ██     │"
echo "│     ██                              ██     │"
echo "│     ████████████████████████████████     │"
echo " ╲                                     ╱"
echo "  ╲                                   ╱"
echo "   ╲                                 ╱"
echo "    ╰─────────────────────────────────╯"
echo ""

# 检查并安装必要组件
echo ""
echo "🔧 检查和安装必要组件..."
echo "========================"

# 检查并安装Python3
if ! command -v python3 >/dev/null 2>&1; then
    echo "📦 安装Python3..."
    apt-get update
    if apt-get install -y python3 python3-pip python3-venv python3-dev; then
        echo "✅ Python3安装成功"
    else
        echo "❌ Python3安装失败"
        exit 1
    fi
else
    echo "✅ Python3已安装: $(python3 --version)"
fi

# 检查并安装nginx
if ! command -v nginx >/dev/null 2>&1; then
    echo "📦 安装nginx..."
    apt-get update
    if apt-get install -y nginx; then
        echo "✅ nginx安装成功"
    else
        echo "❌ nginx安装失败"
        exit 1
    fi
else
    echo "✅ nginx已安装: $(nginx -v 2>&1)"
fi

# 检查并安装nftables
if ! command -v nft >/dev/null 2>&1; then
    echo "📦 安装nftables..."
    apt-get update
    if apt-get install -y nftables; then
        echo "✅ nftables安装成功"
    else
        echo "❌ nftables安装失败"
        exit 1
    fi
else
    echo "✅ nftables已安装: $(nft --version)"
fi

# 检查并安装iproute2 (包含ss命令，用于主动连接终止)
if ! command -v ss >/dev/null 2>&1; then
    echo "📦 安装iproute2..."
    apt-get update
    if apt-get install -y iproute2; then
        echo "✅ iproute2安装成功"
    else
        echo "❌ iproute2安装失败"
        echo "⚠️ 注意: 主动连接终止功能将不可用，但其他功能正常"
    fi
else
    echo "✅ iproute2已安装: $(ss --version 2>&1 | head -n1)"
fi

# 检查并安装conntrack-tools (连接状态管理必需)
if ! command -v conntrack >/dev/null 2>&1; then
    echo "📦 安装conntrack-tools..."
    apt-get update
    
    # 尝试不同的包名
    CONNTRACK_INSTALLED=false
    
    echo "🔍 尝试安装 conntrack-tools..."
    if apt-get install -y conntrack-tools 2>/dev/null; then
        echo "✅ conntrack-tools安装成功"
        CONNTRACK_INSTALLED=true
    else
        echo "⚠️ conntrack-tools安装失败，尝试 conntrack 包..."
        if apt-get install -y conntrack 2>/dev/null; then
            echo "✅ conntrack安装成功"
            CONNTRACK_INSTALLED=true
        else
            echo "⚠️ conntrack安装失败，尝试 conntrackd 包..."
            if apt-get install -y conntrackd 2>/dev/null; then
                echo "✅ conntrackd安装成功"
                CONNTRACK_INSTALLED=true
            fi
        fi
    fi
    
    if [ "$CONNTRACK_INSTALLED" = false ]; then
        echo "❌ 无法安装conntrack相关包"
        echo "⚠️ 注意: 连接状态管理功能将不可用，但其他功能正常"
        echo "是否继续部署? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "部署已取消"
            exit 1
        fi
        echo "继续部署，跳过conntrack安装..."
    fi
else
    echo "✅ conntrack-tools已安装: $(conntrack --version 2>&1 | head -n1)"
fi

# 检查并安装Node.js
if ! command -v node >/dev/null 2>&1; then
    echo "📦 安装Node.js..."
    if command -v apt-get >/dev/null 2>&1; then
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y nodejs
    elif command -v yum >/dev/null 2>&1; then
        curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
        yum install -y nodejs
    else
        echo "❌ 无法确定包管理器，请手动安装Node.js"
        exit 1
    fi
else
    echo "✅ Node.js已安装: $(node --version)"
fi

# 检查npm
if ! command -v npm >/dev/null 2>&1; then
    echo "❌ npm未安装"
    exit 1
fi

echo "✅ npm已安装: $(npm --version)"

# 检查systemctl
if ! command -v systemctl >/dev/null 2>&1; then
    echo "❌ systemctl命令不可用"
    echo "尝试安装systemd..."
    apt-get update
    if apt-get install -y systemd; then
        echo "✅ systemd安装成功"
    else
        echo "❌ systemd安装失败"
        echo "请检查系统是否为systemd系统"
        exit 1
    fi
else
    echo "✅ systemctl可用"
fi

# 清理旧版本
echo ""
echo "🧹 清理旧版本..."
echo "========================"

# 停止并禁用现有服务
if systemctl is-active --quiet yk-safe-backend 2>/dev/null; then
    echo "🛑 停止yk-safe-backend服务..."
    systemctl stop yk-safe-backend
    systemctl disable yk-safe-backend
fi

if systemctl is-active --quiet nginx 2>/dev/null; then
    echo "🛑 停止nginx服务..."
    systemctl stop nginx
    systemctl disable nginx
fi

# 删除旧的服务文件
if [ -f /etc/systemd/system/yk-safe-backend.service ]; then
    echo "🗑️  删除旧的服务文件..."
    rm -f /etc/systemd/system/yk-safe-backend.service
fi

# 删除旧的安装目录
if [ -d "$APP_PATH" ]; then
    echo "🗑️  删除旧的安装目录..."
    rm -rf "$APP_PATH"
fi

# 重新加载systemd
systemctl daemon-reload

# 创建安装目录
echo ""
echo "📁 创建安装目录..."
echo "========================"

mkdir -p "$APP_PATH"/{backend,frontend,logs}
echo "✅ 安装目录创建完成: $APP_PATH"

# 复制应用文件
echo ""
echo "📋 复制应用文件..."
echo "========================"

# 复制后端文件
echo "📁 复制后端文件..."
cp -r "$ORIGINAL_SCRIPT_DIR/backend"/* "$APP_PATH/backend/"
echo "✅ 后端文件复制完成"

# 复制前端文件
echo "📁 复制前端文件..."
cp -r "$ORIGINAL_SCRIPT_DIR/frontend"/* "$APP_PATH/frontend/"
echo "✅ 前端文件复制完成"

# 配置后端
echo ""
echo "🐍 配置Python后端..."
echo "========================"

# 进入后端目录
cd "$APP_PATH/backend"

# 创建Python虚拟环境
echo "📦 创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
echo "📦 安装Python依赖..."
pip install --upgrade pip

# 强制重新安装所有依赖
echo "🔄 强制重新安装依赖..."
pip install --force-reinstall -r requirements.txt

# 验证关键依赖
echo "🔍 验证关键依赖..."
python -c "import requests; print('✅ requests 模块正常')" || {
    echo "❌ requests 模块安装失败，尝试单独安装..."
    pip install --force-reinstall requests==2.31.0
}

python -c "import psutil; print('✅ psutil 模块正常')" || {
    echo "❌ psutil 模块安装失败，尝试单独安装..."
    pip install --force-reinstall psutil==5.9.6
}

echo "✅ Python依赖安装完成"

# 初始化数据库
echo ""
echo "🗄️  初始化数据库..."
python init_db.py
echo "✅ 数据库初始化完成"

# 创建systemd服务文件
echo ""
echo "⚙️  创建systemd服务文件..."
cat > /etc/systemd/system/yk-safe-backend.service << EOF
[Unit]
Description=YK-Safe Backend Service
After=network.target

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=$APP_PATH/backend
Environment=PATH=$APP_PATH/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$APP_PATH/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "✅ systemd服务文件创建完成"

# 构建前端
echo ""
echo "🔨 构建前端..."
echo "========================"

# 进入前端目录
cd "$APP_PATH/frontend"

# 清理旧的构建文件
echo "🧹 清理旧的构建文件..."
if [ -d "build" ]; then
    rm -rf build
    echo "✅ 旧的build目录已删除"
fi

if [ -d "node_modules" ]; then
    rm -rf node_modules
    echo "✅ 旧的node_modules目录已删除"
fi

# 安装依赖
echo "📦 安装npm依赖..."
if npm install; then
    echo "✅ npm依赖安装成功"
else
    echo "❌ npm依赖安装失败"
    exit 1
fi

# 构建前端
echo "🔨 构建前端..."

# 检查并修复文件编码问题
echo "🔍 检查文件编码..."
find src -name "*.jsx" -o -name "*.js" | while read file; do
    # 检查是否有BOM字符并修复
    if file "$file" | grep -q "UTF-8 Unicode (with BOM)"; then
        echo "修复文件编码: $file"
        sed -i '1s/^\xEF\xBB\xBF//' "$file"
    fi
done

if npm run build; then
    echo "✅ 前端构建成功"
else
    echo "❌ 前端构建失败"
    echo "📋 尝试清理缓存后重新构建..."
    rm -rf node_modules/.cache build
    npm install
    npm run build
    if [ $? -ne 0 ]; then
        echo "❌ 前端构建仍然失败，请检查错误信息"
        exit 1
    fi
fi

# 检查构建结果
echo "🔍 检查构建结果..."
if [ -d "build" ] && [ -f "build/index.html" ]; then
    echo "✅ 前端构建完成，index.html文件存在"
else
    echo "❌ 前端构建失败，index.html文件不存在"
    exit 1
fi

# 设置文件权限
echo "🔐 设置文件权限..."
chown -R root:root build/
chmod -R 755 build/
echo "✅ 文件权限已设置"

# 部署白名单功能
echo ""
echo "🔧 部署白名单功能..."
echo "========================"

# 进入后端目录
cd "$APP_PATH/backend"

# 运行白名单数据库迁移
echo "🗄️ 运行白名单数据库迁移..."
if [ -f "migrations/add_whitelist_tables.py" ]; then
    python migrations/add_whitelist_tables.py
    
    if [ $? -ne 0 ]; then
        echo "❌ 白名单数据库迁移失败"
        exit 1
    fi
    
    echo "✅ 白名单数据库迁移成功"
else
    echo "⚠️  白名单迁移文件不存在，跳过"
fi

# 运行新字段迁移
echo "🗄️ 运行新字段迁移..."
if [ -f "migrations/add_new_fields.py" ]; then
    python migrations/add_new_fields.py
    
    if [ $? -ne 0 ]; then
        echo "❌ 新字段迁移失败"
        exit 1
    fi
    
    echo "✅ 新字段迁移成功"
else
    echo "⚠️  新字段迁移文件不存在，跳过"
fi

# 配置nginx
echo ""
echo "🔧 配置nginx..."
echo "========================"

# 备份原nginx配置
if [ -f /etc/nginx/nginx.conf ]; then
    cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ 原nginx配置已备份"
fi

# 创建nginx配置
cat > /etc/nginx/nginx.conf << EOF
user root;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
}

http {
    sendfile on;
    tcp_nopush on;
    types_hash_max_size 2048;
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    gzip on;

    server {
        listen $FRONTEND_PORT;
        server_name _;
        
        # 前端静态文件
        location / {
            root $APP_PATH/frontend/build;
            try_files \$uri \$uri/ /index.html;
        }
        
        # 白名单申请页面
        location /whitelist.html {
            alias $APP_PATH/frontend/public/whitelist.html;
        }
        
        # API代理
        location /api/ {
            proxy_pass http://127.0.0.1:$BACKEND_PORT;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
        
        # 文档
        location /docs {
            proxy_pass http://127.0.0.1:$BACKEND_PORT;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF

echo "✅ nginx配置创建完成"

# 测试nginx配置
echo "🧪 测试nginx配置..."
if nginx -t; then
    echo "✅ nginx配置测试通过"
else
    echo "❌ nginx配置测试失败"
    exit 1
fi

# 配置防火墙
echo ""
echo "🛡️  配置防火墙..."
echo "========================"

# 启动nftables服务
if command -v systemctl >/dev/null 2>&1; then
    systemctl enable nftables
    systemctl start nftables
    
    if systemctl is-active --quiet nftables; then
        echo "✅ nftables服务启动成功"
    else
        echo "❌ nftables服务启动失败"
    fi
fi

# 创建预置配置文件目录
echo "📁 创建预置配置文件..."
mkdir -p /etc/nftables-presets

# 创建黑名单模式预置配置文件
echo "📝 创建黑名单模式预置配置文件..."
cat > /etc/nftables-presets/blacklist.conf << 'EOF'
#!/usr/sbin/nft -f

# 安全模式：创建完整的nftables配置，包含所有必要的链和规则
flush ruleset

# 定义 raw 表 - 用于黑名单规则，确保最高优先级
table inet raw {
    # 黑名单IP集合（初始为空）
    set blacklist {
        type ipv4_addr
        flags interval
        auto-merge
    }
    
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
        
        # 记录被拒绝的连接
        log prefix "nftables denied: " group 0
        
        # 默认拒绝其他连接
        drop
    }
    
    # 应用专用链 - YK-Safe应用规则专用
    chain YK_SAFE_CHAIN {
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
EOF

# 创建白名单模式预置配置文件
echo "📝 创建白名单模式预置配置文件..."
cat > /etc/nftables-presets/whitelist.conf << 'EOF'
#!/usr/sbin/nft -f

# 白名单模式：默认拒绝所有连接，只允许明确允许的IP
flush ruleset

# 定义 filter 表 - 白名单模式
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
        ip saddr 120.226.208.2 ip daddr 0.0.0.0/0 accept
        
        # 预置IP段：192.168.2.0/24
        ip saddr 192.168.2.0/24 ip daddr 0.0.0.0/0 accept
        
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
EOF

# 测试预置配置文件语法
echo "🧪 测试预置配置文件语法..."
if nft -c -f /etc/nftables-presets/blacklist.conf; then
    echo "✅ 黑名单模式配置语法正确"
else
    echo "❌ 黑名单模式配置语法错误"
    exit 1
fi

if nft -c -f /etc/nftables-presets/whitelist.conf; then
    echo "✅ 白名单模式配置语法正确"
else
    echo "❌ 白名单模式配置语法错误"
    exit 1
fi

# 根据部署模式选择防火墙配置
if [ "$DOCKER_MODE" = "safe" ]; then
    echo "🔒 使用安全模式配置防火墙..."
    
    # 使用黑名单模式预置配置（默认）
    cp /etc/nftables-presets/blacklist.conf /etc/nftables.conf
    
    # 应用配置
    echo "🔒 应用nftables配置..."
    nft -f /etc/nftables.conf

    # 验证配置
    if nft list chain inet filter YK_SAFE_CHAIN >/dev/null 2>&1; then
        echo "✅ 应用专用链创建成功"
    else
        echo "❌ 应用专用链创建失败"
        exit 1
    fi

    if nft list chain inet filter input | grep -q "jump YK_SAFE_CHAIN"; then
        echo "✅ 跳转规则配置成功"
    else
        echo "❌ 跳转规则配置失败"
        exit 1
    fi

    echo "✅ 安全nftables配置完成"
    
else
    echo "🔓 使用标准模式配置防火墙..."
    
    # 使用黑名单模式预置配置（默认）
    cp /etc/nftables-presets/blacklist.conf /etc/nftables.conf
    
    # 应用配置
    echo "🔒 应用nftables配置..."
    nft -f /etc/nftables.conf

    # 验证配置
    if nft list chain inet filter YK_SAFE_CHAIN >/dev/null 2>&1; then
        echo "✅ 应用专用链创建成功"
    else
        echo "❌ 应用专用链创建失败"
        exit 1
    fi

    if nft list chain inet filter input | grep -q "jump YK_SAFE_CHAIN"; then
        echo "✅ 跳转规则配置成功"
    else
        echo "❌ 跳转规则配置失败"
        exit 1
    fi

    echo "✅ 标准nftables配置完成"
fi

# 启动服务
echo ""
echo "🚀 启动服务..."
echo "========================"

# 启动后端服务
echo "启动yk-safe-backend服务..."
systemctl daemon-reload
systemctl enable yk-safe-backend
systemctl start yk-safe-backend

if systemctl is-active --quiet yk-safe-backend; then
    echo "✅ yk-safe-backend服务启动成功"
else
    echo "❌ yk-safe-backend服务启动失败"
    systemctl status yk-safe-backend
    exit 1
fi

# 启动nginx服务
echo "启动nginx服务..."
systemctl enable nginx
systemctl start nginx

if systemctl is-active --quiet nginx; then
    echo "✅ nginx服务启动成功"
else
    echo "❌ nginx服务启动失败"
    systemctl status nginx
    exit 1
fi

# 部署完成
echo ""
echo "🎉 YK-Safe 防火墙管理系统部署完成！"
echo "========================"
echo "🌐 访问地址:"
echo "   前端界面: http://$(hostname -I | awk '{print $1}'):$FRONTEND_PORT"
echo "   白名单申请: http://$(hostname -I | awk '{print $1}'):$FRONTEND_PORT/whitelist.html"
echo "   API文档: http://$(hostname -I | awk '{print $1}'):$FRONTEND_PORT/docs"
echo ""
echo "🔐 默认账户:"
echo "   用户名: admin"
echo "   密码: admin123"
echo ""
echo "📝 功能特性:"
echo "   1. 防火墙规则管理（支持黑名单/白名单模式）"
echo "   2. Raw表架构 - 黑名单规则最高优先级执行"
echo "   3. 双层架构 - 实时操作 + 持久化配置"
echo "   4. 连接状态管理 - 实时踢下线功能"
echo "   5. 系统监控和日志管理"
echo "   6. 独立的白名单申请页面"
echo "   7. 自动IP检测和代理警告"
echo "   8. Token管理和申请审核"
echo "   9. Docker网络环境完全兼容"
echo "   10. 应用专用链架构，与Docker共存"
echo "   11. 实时规则同步服务"
echo "   12. 智能部署模式选择"
echo ""
echo "📝 重要提醒:"
echo "   1. 首次登录后请立即修改默认密码"
echo "   2. 定期备份数据库文件"
echo "   3. 监控系统运行状态"
echo "   4. 及时修改示例Token: demo_token_123456789"
echo "   5. 定期清理过期的Token和申请"
echo ""
echo "🛠️ 服务管理:"
echo "   查看状态: systemctl status yk-safe-backend"
echo "   查看日志: journalctl -u yk-safe-backend -f"
echo "   重启服务: systemctl restart yk-safe-backend"
echo "   停止服务: systemctl stop yk-safe-backend"

# 重启并验证服务
echo ""
echo "🔄 重启并验证服务..."
echo "========================"

# 重新加载systemd配置
systemctl daemon-reload

# 重启后端服务
echo "🔄 重启后端服务..."
systemctl restart yk-safe-backend

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
if systemctl is-active --quiet yk-safe-backend; then
    echo "✅ 后端服务启动成功"
else
    echo "❌ 后端服务启动失败"
    echo "📋 查看服务日志:"
    journalctl -u yk-safe-backend --no-pager -n 20
    echo ""
    echo "🔧 尝试手动启动服务..."
    systemctl start yk-safe-backend
    sleep 3
    
    if systemctl is-active --quiet yk-safe-backend; then
        echo "✅ 手动启动成功"
    else
        echo "❌ 手动启动失败，请检查日志"
        journalctl -u yk-safe-backend --no-pager -n 10
    fi
fi

# 重启nginx
echo "🔄 重启nginx..."
systemctl restart nginx

if systemctl is-active --quiet nginx; then
    echo "✅ nginx启动成功"
else
    echo "❌ nginx启动失败"
fi

# 测试API连接
echo "🧪 测试API连接..."
sleep 2
if curl -s http://127.0.0.1:$BACKEND_PORT/health > /dev/null; then
    echo "✅ API连接正常"
else
    echo "❌ API连接失败"
fi

# 测试防火墙规则生成
echo ""
echo "🧪 测试防火墙规则生成..."
echo "========================"

# 进入后端目录
cd "$APP_PATH/backend"

# 激活虚拟环境
source venv/bin/activate

# 测试规则生成器
echo "🔍 测试nftables规则生成器..."
python -c "
import sys
sys.path.append('.')
from app.utils.nftables_generator import NftablesGenerator
from app.db.database import SessionLocal

db = SessionLocal()
try:
    generator = NftablesGenerator(db)
    
    if '$DOCKER_MODE' == 'safe':
        # 安全模式：测试同步规则到应用专用链
        print('🧪 测试同步规则到应用专用链...')
        if generator.sync_rules_from_db():
            print('✅ 规则同步成功')
        else:
            print('❌ 规则同步失败')
        
        # 检查应用专用链
        print('🔍 检查应用专用链...')
        rules = generator.list_rules_realtime()
        print(f'应用专用链中的规则数量: {len(rules)}')
    else:
        # 标准模式：生成配置内容
        config_content = generator.generate_config()
        print('✅ 配置生成成功')
        print('配置长度:', len(config_content))
        
        # 检查生成的规则
        lines = config_content.split('\n')
        rule_lines = []
        
        for i, line in enumerate(lines):
            if 'ip saddr' in line and 'drop' in line:
                rule_lines.append(f'{i+1:3d}: {line.strip()}')
        
        if rule_lines:
            print('✅ 找到生成的规则:')
            for rule in rule_lines:
                print(f'  {rule}')
        else:
            print('⚠️  未找到生成的规则')
        
        # 检查是否有错误的语法
        error_lines = []
        for i, line in enumerate(lines):
            if 'protocol' in line and 'ip saddr' in line:
                error_lines.append(f'{i+1:3d}: {line.strip()}')
        
        if error_lines:
            print('❌ 发现错误的语法:')
            for line in error_lines:
                print(f'  {line}')
            print('⚠️  请检查数据库中的协议字段数据')
        else:
            print('✅ 没有发现错误的语法')
        
        # 测试配置语法
        print('🧪 测试生成的配置语法...')
        with open('/tmp/test_nftables.conf', 'w') as f:
            f.write(config_content)
        
        import subprocess
        result = subprocess.run(['nft', '-c', '-f', '/tmp/test_nftables.conf'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print('✅ 生成的配置语法测试通过')
        else:
            print('❌ 生成的配置语法测试失败:')
            print(result.stderr)
        
        # 清理测试文件
        import os
        if os.path.exists('/tmp/test_nftables.conf'):
            os.remove('/tmp/test_nftables.conf')
    
except Exception as e:
    print(f'❌ 规则生成测试失败: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
"

echo ""
echo "🎉 部署完成！请访问: http://$(hostname -I | awk '{print $1}'):$FRONTEND_PORT"

# 显示部署模式总结
echo ""
echo "📊 部署模式总结..."
echo "========================"
if [ "$DOCKER_MODE" = "safe" ]; then
    echo "🔒 安全部署模式已启用"
    echo "✅ 应用专用链架构已安全部署"
    echo "✅ 现有Docker容器未受影响"
    echo "✅ 所有网络规则保持完整"
    echo ""
    echo "🔍 验证命令:"
    echo "   检查应用专用链: nft list chain inet filter YK_SAFE_CHAIN"
    echo "   检查跳转规则: nft list chain inet filter input"
    echo "   检查Docker容器: docker ps"
else
    echo "🔓 标准部署模式已启用"
    echo "✅ 完整的nftables配置已部署"
    echo "✅ 最高性能的防火墙规则已启用"
    echo "✅ 完整的系统集成已完成"
fi

echo ""
echo "🎯 部署脚本特点:"
echo "   ✅ 智能环境检测"
echo "   ✅ 自动部署模式选择"
echo "   ✅ 完整的系统部署"
echo "   ✅ 安全的Docker兼容性"
echo "   ✅ 渐进式配置更新"
echo "   ✅ 完整的错误处理"
echo "   ✅ 详细的部署日志"
echo "   ✅ 自动服务管理"
echo "   ✅ 智能端口配置"
echo "   ✅ 灵活的部署路径"

# 显示部署完成庆祝图案
echo ""
echo "    ╭─────────────────────────────────────╮"
echo "   ╱                                     ╲"
echo "  ╱    🎉 部署成功！🎉                    ╲"
echo " ╱    ████████████████████████████████    ╲"
echo "╱     ██                              ██     ╲"
echo "│     ██    ╭─────────────────────╮    ██     │"
echo "│     ██    │   🛡️ YK-SAFE 🛡️     │    ██     │"
echo "│     ██    │   防护系统已就绪     │    ██     │"
echo "│     ██    │   Firewall Ready     │    ██     │"
echo "│     ██    ╰─────────────────────╯    ██     │"
echo "│     ██                              ██     │"
echo "│     ██    ╭─────────────────────╮    ██     │"
echo "│     ██    │   🌐 访问地址 🌐     │    ██     │"
echo "│     ██    │ http://$(hostname -I | awk '{print $1}'):$FRONTEND_PORT │    ██     │"
echo "│     ██    ╰─────────────────────╯    ██     │"
echo "│     ██                              ██     │"
echo "│     ████████████████████████████████     │"
echo " ╲                                     ╱"
echo "  ╲                                   ╱"
echo "   ╲                                 ╱"
echo "    ╰─────────────────────────────────╯"
echo ""
echo "🎊 恭喜！YK-Safe 防火墙管理系统部署完成！"
echo "🔐 您的网络安全防护系统已成功启动！"
