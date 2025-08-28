# YK-Safe 防火墙管理系统

一个基于 FastAPI + React 的现代化防火墙管理系统，专为 Debian/Ubuntu 系统设计，支持 Docker 环境部署。

## 🚀 功能特性

### 核心功能
- **防火墙规则管理**: 支持黑名单/白名单模式切换
- **系统监控**: 实时监控 CPU、内存、网络等系统资源
- **日志管理**: 查看和管理系统日志
- **用户认证**: 基于 JWT 的用户认证系统

### 白名单功能
- **独立申请页面**: 免登录的白名单IP申请页面
- **自动IP检测**: 自动获取浏览器公网IP地址
- **代理检测**: 检测并警告代理/VPN使用
- **Token管理**: 支持Token创建、管理和使用限制
- **申请审核**: 完整的申请审核流程
- **自动规则创建**: 审核通过后自动创建防火墙规则

### Docker支持
- **网络兼容**: 自动配置Docker网络支持
- **容器通信**: 不影响Docker容器间通信
- **环境检测**: 自动检测Docker环境并适配

## 🛠️ 技术栈

### 后端
- **FastAPI**: 现代化的Python Web框架
- **SQLAlchemy**: ORM数据库操作
- **nftables**: Linux防火墙管理
- **psutil**: 系统监控
- **JWT**: 用户认证

### 前端
- **React 18**: 用户界面框架
- **Ant Design**: UI组件库
- **Axios**: HTTP客户端
- **ECharts**: 数据可视化
- **React Router**: 路由管理

### 部署
- **systemd**: 服务管理
- **Nginx**: 反向代理和静态文件服务
- **Docker**: 容器化支持

## 📦 快速部署

### 系统要求
- **操作系统**: Debian 11+ 或 Ubuntu 20.04+
- **权限**: 需要 root 权限运行部署脚本
- **网络**: 需要互联网连接下载依赖包

### 一键部署
```bash
# 克隆项目
git clone <repository-url>
cd yk-safe

# 运行部署脚本（仅支持 Debian/Ubuntu）
sudo ./deploy.sh
```

### 部署后访问
- **主系统**: http://your-server:5023/
- **白名单申请**: http://your-server:5023/whitelist.html
- **API文档**: http://your-server:5023/docs

### 默认账户
- **用户名**: admin
- **密码**: admin123

## 🎯 使用指南

### 防火墙管理
1. 登录系统后进入"防火墙"页面
2. 选择防火墙模式（黑名单/白名单）
3. 添加、编辑或删除防火墙规则
4. 规则变更后自动重新加载防火墙

### 白名单申请
1. 访问白名单申请页面
2. 填写公司名称和Token
3. 系统自动获取IP地址
4. 提交申请等待审核
5. 管理员审核通过后自动创建规则

### Token管理
1. 在管理后台创建Token
2. 设置使用次数限制和过期时间
3. 将Token分发给需要申请白名单的用户
4. 监控Token使用情况

## 🔧 配置说明

### 防火墙模式
- **黑名单模式**: 默认允许所有连接，只拒绝明确配置的规则
- **白名单模式**: 默认拒绝所有连接，只允许明确配置的规则

### Docker网络支持
系统自动配置以下网络段：
- 默认网桥: 172.17.0.0/16
- 自定义网络: 172.18.0.0/15, 172.20.0.0/14, 172.24.0.0/13, 172.32.0.0/11
- IPv6网络: fd00::/8

## 📝 重要提醒

1. **安全**: 首次登录后立即修改默认密码
2. **备份**: 定期备份数据库文件
3. **监控**: 监控系统运行状态和资源使用
4. **Token管理**: 及时修改示例Token，定期清理过期Token
5. **防火墙**: 确保SSH端口不被误封，避免锁定

## 🛠️ 服务管理

```bash
# 查看服务状态
systemctl status yk-safe-backend

# 重启服务
systemctl restart yk-safe-backend

# 查看日志
journalctl -u yk-safe-backend -f

# 停止服务
systemctl stop yk-safe-backend
```

## 📁 项目结构

```
yk-safe/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API接口
│   │   ├── db/             # 数据库模型
│   │   ├── schemas/        # 数据验证
│   │   └── utils/          # 工具函数
│   ├── migrations/         # 数据库迁移
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端代码
│   ├── public/            # 静态文件
│   ├── src/               # 源代码
│   └── package.json       # Node.js依赖
├── deploy.sh              # 一键部署脚本
└── README.md              # 项目文档
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 📄 许可证

本项目采用 MIT 许可证。