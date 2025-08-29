# YK-Safe 更新日志 (CHANGELOG)

## 📋 目录
- [项目概述](#项目概述)
- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [更新记录](#更新记录)
  - [防火墙架构重构](#防火墙架构重构)
  - [Docker容器监控优化](#docker容器监控优化)
  - [Dashboard界面优化](#dashboard界面优化)
  - [IP地址获取和验证修复](#ip地址获取和验证修复)
  - [防火墙日志系统](#防火墙日志系统)
  - [Token管理模块](#token管理模块)
  - [GeoIP集成](#geoip集成)
  - [白名单申请页面优化](#白名单申请页面优化)
  - [错误处理改进](#错误处理改进)
  - [前端构建修复](#前端构建修复)
  - [部署脚本优化](#部署脚本优化)
- [部署说明](#部署说明)
- [技术支持](#技术支持)

---

## 🎯 项目概述

YK-Safe 是一个专为 Debian/Ubuntu 系统设计的现代化防火墙管理系统，基于 FastAPI + React 构建。系统提供了完整的防火墙规则管理、系统监控、白名单申请、Token管理等功能。

## ✅ 核心功能

### **防火墙管理**
- 支持黑名单/白名单模式切换
- Raw表架构 - 黑名单规则最高优先级执行
- 双层架构 - 实时操作 + 持久化配置
- 连接状态管理 - 实时踢下线功能

### **系统功能**
- 系统监控和日志管理
- 独立的白名单申请页面
- 自动IP检测和代理警告
- Token管理和申请审核
- Docker网络环境完全兼容
- 实时规则同步服务

## 🛠️ 技术架构

### **后端**
- FastAPI (Python Web框架)
- SQLAlchemy (ORM)
- nftables (防火墙管理)
- conntrack-tools (连接状态管理)
- psutil (系统监控)

### **前端**
- React 18
- Ant Design
- ECharts (数据可视化)

### **部署**
- systemd (服务管理)
- Nginx (反向代理)
- apt-get (包管理)

---

## 📝 更新记录

### 🔥 防火墙架构重构 (2024年8月)

#### **问题描述**
原有的 `nftables` 配置使用 `flush ruleset` 导致网络 disruptions，清除了 Docker 的网络规则，造成"核弹级问题"。

#### **解决方案**
1. **消除 `flush ruleset`**: 停止清空整个 `nftables` 规则集
2. **专用应用链**: 创建专门的 `nftables` 链 (`YK_SAFE_CHAIN`) 在 `filter` 表中
3. **跳转规则**: 在 `filter` 表的 `input` 链中插入 `jump` 规则重定向到 `YK_SAFE_CHAIN`
4. **部署脚本集成**: 修改 `deploy.sh` 执行一次性创建专用链和跳转规则

#### **技术实现**
- **`nftables_generator.py` 重构**:
  - 移除所有 `flush ruleset` 和 `/etc/nftables.conf` 写入逻辑
  - 修改 `add_rule_realtime` 直接添加规则到 `YK_SAFE_CHAIN`
  - 修改 `delete_rule_realtime` 直接从 `YK_SAFE_CHAIN` 删除规则
  - 引入新的 `sync_rules_from_db` 方法替换 `apply_config`
- **防火墙API更新**: 调整后端API使用新的 `sync_rules_from_db` 方法

#### **文件修改**
- `deploy.sh`: 添加 `jump YK_SAFE_CHAIN` 规则和 `YK_SAFE_CHAIN` 定义
- `nftables_generator.py`: 重构核心逻辑，移除 `flush ruleset`
- `firewall.py`: 修改 `reload_nftables` 调用 `generator.sync_rules_from_db()`

---

### 🐳 Docker容器监控优化 (2024年8月)

#### **问题描述**
原有的 `get_container_info` 实现使用 `subprocess.run` 调用 `docker` 命令，效率低下且不一致。

#### **解决方案**
使用官方 `Docker SDK for Python` 替换 `subprocess.run` 实现。

#### **技术实现**
```python
import docker

def get_container_info():
    client = docker.from_env()
    containers = client.containers.list()
    
    container_info = []
    for container in containers:
        info = {
            'name': container.name,
            'status': container.status,
            'image': container.image.tags[0] if container.image.tags else container.image.id,
            'ports': container.ports,
            'mounts': container.attrs.get('Mounts', []),
            'short_id': container.short_id,
            'created': container.attrs.get('Created', '')
        }
        
        # 只为运行中的容器获取实时统计
        if container.status == 'running':
            try:
                stats = container.stats(stream=False)
                info['stats'] = stats
            except Exception as e:
                info['stats'] = None
        
        container_info.append(info)
    
    return container_info
```

#### **优化特性**
- **端口映射解析**: 改进 `container.ports` 解析，格式化为 `HostIp:HostPort->ContainerPort`
- **挂载信息获取**: 从 `container.attrs` (高级API) 获取挂载信息，提高一致性和效率
- **挂载格式**: 将原始挂载字典格式化为可读字符串列表
- **条件统计**: 只为 `running` 状态的容器获取实时统计

---

### 🎨 Dashboard界面优化 (2024年8月)

#### **移除功能**
- 删除"磁盘使用情况"卡片
- 删除"最近系统日志"卡片

#### **系统负载卡片增强**
- 添加磁盘使用信息，支持多磁盘显示
- 系统负载超过1.5倍CPU核心数时显示黄色警告徽章
- 系统负载超过2.5倍CPU核心数时显示红色警告徽章

#### **磁盘使用显示优化**
- 磁盘使用超过80%时显示黄色警告徽章
- 磁盘使用超过95%时显示红色警告徽章
- 数值显示保留2位小数

#### **CPU使用率卡片增强**
- 显示CPU核心数量
- 以美观方式显示所有核心的使用率

#### **Docker容器监控卡片增强**
- 显示端口映射（之前未显示）
- 显示路径映射（卷），排除时区映射

#### **防火墙状态显示优化**
- 防火墙状态使用徽章显示（绿色运行、红色停止、黄色未知）
- 防火墙模式使用黑白文本显示
- 将防火墙状态和模式显示从"系统概览"移动到页面顶部标题栏左侧

---

### 🌐 IP地址获取和验证修复 (2024年12月)

#### **关键问题分析**
1. **API端点调用错误**: `detectNetworkEnvironment` 函数调用 `${API_BASE}/public/ip` 返回服务器IP而非访客真实IP
2. **IP输入框只读状态管理**: API调用失败时输入框保持 `readonly` 状态，用户无法手动输入
3. **IP格式验证缺失**: 缺乏对输入IP地址的格式验证和私有IP检测

#### **修复方案**
1. **多重IP获取策略**:
   - 第三方服务优先（如 `api.ipify.org`）
   - 后端API备用
   - 完善的错误处理

2. **完善的错误处理和状态管理**:
   - 确保任何错误情况下输入框都是可编辑的
   - 提供清晰的用户提示
   - 不阻塞用户操作

3. **增强的IP地址验证**:
   - 实时格式验证
   - 私有IP地址检测
   - 公网IP地址确认
   - 用户友好的错误提示

#### **技术实现**
```javascript
// 多重IP获取策略
try {
    const thirdPartyResponse = await fetch('https://api.ipify.org?format=json', {
        method: 'GET',
        signal: AbortSignal.timeout(5000)
    });
    
    if (thirdPartyResponse.ok) {
        const thirdPartyData = await thirdPartyResponse.json();
        publicIp = thirdPartyData.ip;
        ipSource = '第三方服务';
    }
} catch (thirdPartyError) {
    console.log('第三方服务获取IP失败:', thirdPartyError.message);
}

// 后端API备用
if (!publicIp) {
    try {
        const ipResponse = await fetch(`${API_BASE}/public/ip`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
            signal: AbortSignal.timeout(8000)
        });
        
        if (ipResponse.ok) {
            const ipData = await ipResponse.json();
            publicIp = ipData.ip;
            ipSource = '后端API';
        }
    } catch (backendError) {
        console.log('后端API获取IP失败:', backendError.message);
    }
}
```

#### **IP验证功能**
```javascript
// IP地址格式验证
function isValidIP(ip) {
    if (!ip || typeof ip !== 'string') {
        return false;
    }
    
    const ipPattern = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    return ipPattern.test(ip.trim());
}

// 私有IP地址检测
function isPrivateIP(ip) {
    if (!isValidIP(ip)) {
        return false;
    }
    
    const parts = ip.split('.').map(Number);
    const first = parts[0];
    const second = parts[1];
    
    return (
        (first === 10) ||                                    // 10.x.x.x
        (first === 172 && second >= 16 && second <= 31) ||   // 172.16-31.x.x
        (first === 192 && second === 168) ||                 // 192.168.x.x
        (first === 127) ||                                   // 127.x.x.x (本地回环)
        (first === 169 && second === 254) ||                 // 169.254.x.x (链路本地)
        (first === 0)                                        // 0.x.x.x
    );
}
```

---

### 📊 防火墙日志系统 (2024年8月)

#### **功能特性**
- **详细日志记录**: 连接信息、动作记录、规则关联、网络细节、地理位置、威胁评估
- **智能威胁评估**: 端口风险、协议分析、动作权重、地理位置风险评估
- **高性能设计**: 异步处理、批量插入、队列缓冲、索引优化
- **统计分析**: 实时统计、趋势分析、热门IP、动作分布
- **管理功能**: 灵活查询、分页支持、日志导出、自动清理

#### **系统架构**
```sql
CREATE TABLE firewall_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_ip TEXT,                    -- 源IP地址
    destination_ip TEXT,               -- 目标IP地址
    protocol TEXT,                     -- 协议类型
    source_port INTEGER,               -- 源端口
    destination_port INTEGER,          -- 目标端口
    action TEXT,                       -- 防火墙动作
    rule_id INTEGER,                   -- 关联规则ID
    rule_name TEXT,                    -- 规则名称
    interface TEXT,                    -- 网络接口
    packet_size INTEGER,               -- 数据包大小
    tcp_flags TEXT,                    -- TCP标志
    country TEXT,                      -- 源IP国家
    city TEXT,                         -- 源IP城市
    isp TEXT,                          -- 网络服务商
    threat_level TEXT,                 -- 威胁等级
    description TEXT,                  -- 详细描述
    timestamp DATETIME                 -- 时间戳
);
```

#### **核心组件**
1. **FirewallLogger**: 日志记录器核心类
2. **日志队列**: 内存缓冲队列
3. **工作线程**: 异步日志处理
4. **地理位置服务**: IP地理位置查询
5. **威胁评估引擎**: 自动威胁等级计算

#### **API接口**
- `GET /api/logs/firewall` - 获取防火墙日志
- `GET /api/logs/stats` - 获取日志统计
- `GET /api/logs/firewall/summary` - 获取日志摘要
- `GET /api/logs/firewall/export` - 导出日志
- `POST /api/logs/firewall/cleanup` - 清理旧日志

---

### 🔑 Token管理模块 (2024年8月)

#### **核心功能**
1. **Token管理**: 创建、配置、状态管理、安全操作
2. **Token验证**: 格式验证、状态检查、安全验证
3. **使用统计**: 使用情况、请求统计、趋势分析
4. **审计日志**: 操作记录、用户追踪、日志导出

#### **后端API**
- **Token管理API** (`/api/tokens/`): 创建、批量创建、获取、更新、删除、激活/停用、重新生成、使用情况、统计概览
- **Token审计API** (`/api/token-audit/`): 审计日志、操作统计、导出、清理、最近日志

#### **数据库模型**
```sql
CREATE TABLE whitelist_tokens (
    id INTEGER PRIMARY KEY,
    token VARCHAR UNIQUE NOT NULL,
    company_name VARCHAR NOT NULL,
    description TEXT,
    max_uses INTEGER DEFAULT 100,
    used_count INTEGER DEFAULT 0,
    expires_at DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    auto_approve BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR,
    updated_at DATETIME
);
```

#### **工具函数**
- `generate_secure_token()` - 生成安全的随机Token
- `validate_token_format()` - 验证Token格式
- `verify_token()` - 验证Token有效性
- `increment_token_usage()` - 增加Token使用次数
- `log_token_action()` - 记录Token操作日志

---

### 🌍 GeoIP集成 (2024年8月)

#### **主要改进**
1. **GeoIP数据库集成**: 集成GeoLite2-City.mmdb数据库
2. **后端API改进**: 新增网络连接监控API端点
3. **前端界面改进**: 网络连接弹窗扩展，地理位置显示
4. **GeoIP工具类**: GeoIPManager类和便捷函数

#### **新增API端点**
1. **`GET /api/monitor/connections`**: 获取详细的网络连接信息，包含IP地理位置
2. **`GET /api/monitor/connections/{ip}`**: 获取特定IP地址的连接详情

#### **功能特性**
- **IP分组统计**: 按远程IP地址分组统计连接数
- **地理位置查询**: 自动查询IP地址的地理位置信息
- **本地IP识别**: 自动识别本地网络和私有IP地址
- **连接状态统计**: 统计TCP/UDP连接状态分布

#### **GeoIP工具类**
```python
class GeoIPManager:
    - get_ip_info(ip_address): 获取详细地理位置信息
    - get_simple_ip_info(ip_address): 获取简化地理位置信息
    - get_ip_summary(ip_address): 获取地理位置摘要
```

#### **便捷函数**
```python
- get_ip_location(ip_address): 获取详细地理位置信息
- get_ip_location_simple(ip_address): 获取简化地理位置信息
- get_ip_location_summary(ip_address): 获取地理位置摘要
```

---

### 📝 白名单申请页面优化 (2024年8月)

#### **Token模块集成**
- **后端改进**: 更新 `whitelist.py` API，集成新的token相关schemas和工具函数
- **前端改进**: 改进token验证流程，添加详细错误处理和日志记录

#### **IP获取功能优化**
- **后端改进**: 优化 `ip_utils.py`，减少外部服务请求超时时间，添加IP有效性验证
- **前端改进**: 改进IP获取流程，添加请求超时处理，改进错误处理和用户提示

#### **表单提交优化**
- **数据验证**: 添加基本字段验证，使用 `trim()` 去除输入字段的首尾空格
- **错误处理**: 添加详细的错误分类和处理，改进错误提示信息的可读性
- **用户体验**: 保持IP地址字段的值，提供更详细的操作反馈信息

#### **IP位置信息功能**
- **视觉设计**: 优雅的渐变背景、圆角边框、动画效果、响应式布局
- **信息展示**: 国家/地区、城市、地区、时区信息，支持国旗emoji显示
- **交互体验**: 自动获取、实时更新、加载状态、手动输入、实时验证

---

### ⚠️ 错误处理改进 (2024年8月)

#### **主要改进**
1. **deploy.sh脚本改进**: 增强的包安装逻辑、用户交互式处理、完整的错误处理
2. **nftables_generator.py改进**: 连接管理容错、连接查询容错

#### **多包名尝试机制**
```bash
# 尝试不同的包名
if apt-get install -y conntrack-tools 2>/dev/null; then
    echo "✅ conntrack-tools安装成功"
elif apt-get install -y conntrack 2>/dev/null; then
    echo "✅ conntrack安装成功"
elif apt-get install -y conntrackd 2>/dev/null; then
    echo "✅ conntrackd安装成功"
fi
```

#### **用户交互处理**
```bash
if [ "$CONNTRACK_INSTALLED" = false ]; then
    echo "⚠️ 注意: 连接状态管理功能将不可用，但其他功能正常"
    echo "是否继续部署? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "部署已取消"
        exit 1
    fi
    echo "继续部署，跳过conntrack安装..."
fi
```

#### **优雅降级处理**
```python
def _terminate_active_connections(self, ip_address: str) -> bool:
    try:
        subprocess.run(['conntrack', '-h'], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.warning("`conntrack` 命令未找到或无法执行。连接状态管理功能不可用。")
        logger.info("IP已被添加到黑名单，新连接将被拦截，但现有连接可能继续存在。")
        return False
```

---

### 🔧 前端构建修复 (2024年8月)

#### **问题描述**
前端构建失败，出现以下错误：
```
Module not found: Error: Can't resolve 'react-copy-to-clipboard' in '/opt/yk-safe/frontend/src/pages'
```

#### **问题原因**
1. **缺失依赖**: `TokenManagement.jsx` 文件中使用了 `react-copy-to-clipboard` 包，但在 `package.json` 中没有声明
2. **语法错误**: `Dashboard.jsx` 文件中存在注释语法错误

#### **解决方案**
1. **添加缺失的依赖**: 在 `frontend/package.json` 中添加 `react-copy-to-clipboard` 依赖
2. **修复语法错误**: 修复 `Dashboard.jsx` 中的注释语法错误

#### **修复结果**
- ✅ 依赖安装成功
- ✅ 构建成功
- ✅ TokenManagement页面复制功能正常
- ✅ Dashboard页面正常显示

---

### 🚀 部署脚本优化 (2024年8月)

#### **deploy.sh优化**
- 添加Docker容器状态检查，在应用nftables配置前提示用户确认
- 提供网络恢复建议
- 包含交互式端口配置（FRONTEND_PORT, BACKEND_PORT）
- 修改文件复制逻辑，确保不删除源目录文件

#### **deploy-safe.sh创建**
- 专为有现有Docker容器的环境设计的安全部署脚本
- 应用nftables规则时不使用 `flush ruleset`
- 交互式端口配置和部署路径选择
- 完整的系统环境检查和自动安装

#### **关键特性**
- **安全模式**: 不干扰现有Docker网络配置
- **路径选择**: 用户可选择部署路径，默认 `/opt/$APP_NAME`
- **端口配置**: 交互式配置前端端口（默认5023）和后端端口（默认8000）
- **环境检查**: 自动检查并安装缺失的系统组件
- **文件管理**: 智能的文件复制和清理逻辑

---

## 🚀 部署说明

### **系统要求**
- **操作系统**: Debian 11+ 或 Ubuntu 20.04+
- **权限**: root 权限
- **网络**: 互联网连接

### **自动安装的依赖**
- Python3 + pip + venv
- nginx
- nftables
- conntrack-tools
- systemd

### **部署流程**
```bash
# 克隆项目
git clone <repository-url>
cd yk-safe

# 运行部署脚本
sudo ./deploy.sh

# 或者使用安全部署脚本（推荐有Docker容器的环境）
sudo ./deploy-safe.sh
```

### **部署后访问**
- **主系统**: http://your-server:5023/
- **白名单申请**: http://your-server:5023/whitelist.html
- **API文档**: http://your-server:5023/docs

### **默认账户**
- **用户名**: admin
- **密码**: admin123

### **服务管理**
```bash
# 查看状态
systemctl status yk-safe-backend

# 重启服务
systemctl restart yk-safe-backend

# 查看日志
journalctl -u yk-safe-backend -f

# 停止服务
systemctl stop yk-safe-backend
```

---

## 📞 技术支持

如果在部署或使用过程中遇到问题，请：

1. 查看浏览器控制台错误信息
2. 检查系统日志和防火墙状态
3. 验证网络连接和API状态
4. 联系技术支持团队

---

**项目状态**: ✅ 已完成  
**测试状态**: ✅ 已验证  
**支持系统**: Debian/Ubuntu  
**最后更新**: 2024年12月  
**文档版本**: 1.0.0

# YK-Safe 更新记录

## [2025-01-XX] 系统功能修复和优化

### 🔧 网络工具功能修复
- **修复ping命令无数据返回问题**：重构后端API，使用正确的进程管理和输出捕获
- **修复traceroute命令无数据返回问题**：优化命令执行逻辑，确保正确获取输出结果
- **添加停止功能**：为ping和traceroute命令添加停止按钮，支持中断正在执行的命令
- **修复抓包停止功能500错误**：重构抓包停止逻辑，正确处理进程终止
- **修复抓包时长参数不生效问题**：实现定时器机制，确保抓包在指定时间后自动停止
- **优化前端API调用**：更新前端代码使用正确的API端点

### 🎨 前端界面优化
- **修复侧边栏固定问题**：设置侧边栏为固定定位，不随页面滚动
- **恢复专业深色主题**：替换小清新风格为更专业的深蓝色主题
- **优化颜色搭配**：使用标准的Ant Design配色方案，提升视觉体验
- **统一组件样式**：确保所有页面使用一致的主题和样式

### 💾 数据备份功能修复
- **修复备份文件大小为0的问题**：优化备份逻辑，确保正确创建和压缩文件
- **添加备份信息文件**：在备份包中包含说明文件，记录备份时间和内容
- **增强错误处理**：添加详细的日志输出，便于调试备份问题
- **验证文件创建**：确保备份文件成功创建并记录正确的大小

### 🛡️ 防火墙模式切换优化
- **确保白名单模式生效**：验证预置配置文件的存在和应用
- **优化模式切换逻辑**：改进配置文件的备份和恢复机制
- **增强错误处理**：添加详细的错误信息和回滚机制

### ⚡ 系统稳定性提升
- **修复后端服务启动失败**：解决命名冲突问题，确保所有路由正确注册
- **优化进程管理**：改进后台任务的进程管理和资源清理
- **增强错误日志**：添加详细的调试信息，便于问题排查

### 📝 代码质量改进
- **重构网络工具API**：统一API设计，提高代码可维护性
- **优化数据库操作**：改进事务处理和错误处理
- **增强前端交互**：优化用户界面响应和状态管理
  - 统一了圆角、阴影、间距等设计规范

- **登录页面美化**:
  - 应用了渐变背景和装饰性元素
  - 卡片采用毛玻璃效果和柔和阴影
  - 输入框和按钮采用圆角设计

- **防火墙状态显示**:
  - 状态徽章采用小清新配色
  - 运行/停止状态使用不同颜色的徽章
  - 模式显示采用信息色徽章

- **页面卡片样式**:
  - 所有卡片添加了悬停效果
  - 系统负载卡片使用特殊背景色
  - 网络连接卡片使用渐变背景
  - 工具卡片和设置卡片使用不同配色

- **组件样式统一**:
  - 按钮、输入框、表格等组件采用统一的小清新风格
  - 开关组件使用主题色
  - 进度条使用渐变效果
  - 标签使用半透明背景

### 🎨 交互体验
- **动画效果**: 添加了淡入动画和悬停效果
- **自定义滚动条**: 使用主题色的滚动条样式
- **状态反馈**: 所有状态显示都采用小清新配色方案

### 🎨 配色方案
- **主色调**: #7FB069 (薄荷绿)
- **辅助色**: #A8D5BA (淡蓝绿)
- **背景色**: #FAFDF7 (淡米白)
- **成功色**: #7FB069 (薄荷绿)
- **警告色**: #F4A261 (暖橙色)
- **错误色**: #E76F51 (珊瑚红)
- **信息色**: #A8D5BA (淡蓝绿)

---

## [2025-01-XX] 网络工具和系统设置功能

### 🛠️ 新增功能
- **网络工具页面**:
  - TCPDump 抓包工具（支持协议、网卡、IP过滤、时长设置）
  - Ping 测试工具（实时输出显示）
  - 路由追踪工具（实时输出显示）
  - 抓包历史管理（下载、删除功能）

- **系统设置页面**:
  - 密码修改功能
  - 数据备份功能（创建、下载、删除、恢复）
  - 推送设置（Webhook、Bark推送，支持飞书、钉钉、微信等）

### 🔧 技术实现
- **后端API**: 新增 `network.py` 和 `settings.py` 路由
- **数据库模型**: 新增 `NetworkCapture`、`NetworkTask`、`SystemBackup`、`PushConfig` 模型
- **前端页面**: 新增 `NetworkTools.jsx` 和 `Settings.jsx` 组件
- **导航菜单**: 在左侧导航栏添加"网络工具"和"系统设置"入口

### 🎯 功能特性
- **异步任务处理**: 使用 FastAPI BackgroundTasks 处理长时间运行的任务
- **实时状态更新**: 通过轮询获取任务执行状态和进度
- **文件管理**: 自动压缩抓包文件，支持下载和清理
- **推送通知**: 支持多种推送渠道和消息类型选择

---

## [2025-01-XX] 防火墙模式切换优化

### 🔧 核心改进
- **预设配置文件系统**: 
  - 部署时创建 `/etc/nftables-presets/` 目录
  - 预设 `blacklist.conf` 和 `whitelist.conf` 配置文件
  - 默认使用黑名单模式部署

- **模式切换逻辑优化**:
  - 首次切换时备份当前配置
  - 应用对应模式的预设配置文件
  - 同步现有规则到新配置
  - 支持配置回滚功能

### 🛡️ 白名单模式增强
- **预设IP支持**: 白名单模式自动包含 `120.226.208.2` 和 `192.168.2.0/24`
- **默认策略**: 白名单模式下默认拒绝所有连接，只允许明确添加的IP

### 🔧 技术实现
- **新增工具模块**: `mode_switch_sync.py` 处理规则同步
- **配置备份**: 自动备份和恢复功能
- **错误处理**: 完善的错误处理和回滚机制

---

## [2025-01-XX] 防火墙规则管理重构

### 🔧 核心改进
- **规则动作选择**: 新增规则时可选择"拒绝"或"允许"动作
- **模式相关逻辑**: 黑名单模式应用拒绝规则，白名单模式应用允许规则
- **搜索和筛选**: 支持按规则名称、备注搜索，按动作类型筛选

### 🎯 用户体验
- **规则来源显示**: 区分"手工添加"和"自助提交"
- **重复IP检测**: 防止添加重复IP地址的规则
- **布局优化**: 合并标题和操作按钮，改善页面布局

### 🔧 技术实现
- **前端优化**: 重构 `FirewallRules.jsx` 组件
- **后端增强**: 完善规则验证和重复检测逻辑
- **数据一致性**: 确保 `whitelist.html` 提交的规则正确显示

---

## [2025-01-XX] 部署脚本优化

### 🔧 核心改进
- **脚本合并**: 将 `deploy.sh` 和 `deploy-safe.sh` 合并为单一智能脚本
- **环境检测**: 自动检测Docker环境和系统类型
- **条件部署**: 根据环境选择合适的部署策略

### 🛡️ 防火墙配置
- **完整配置生成**: 部署时生成完整的 `nftables.conf` 文件
- **原子操作**: 使用 `nft -f /etc/nftables.conf` 确保配置一致性
- **Docker兼容**: 确保防火墙规则与Docker网络兼容

### 🔧 技术实现
- **智能检测**: 检测Docker容器、系统类型、用户权限
- **错误处理**: 完善的错误处理和回滚机制
- **日志记录**: 详细的部署过程日志

---

## [2025-01-XX] 前端界面优化

### 🎨 界面改进
- **防火墙状态显示**: 在页面头部显示防火墙状态、模式和控制开关
- **模式切换**: 添加模式切换开关，支持二次确认
- **状态徽章**: 优化各种状态显示的颜色和样式

### 🔧 功能增强
- **实时监控**: 仪表盘数据自动刷新
- **Docker监控**: 显示容器端口映射和挂载信息
- **网络监控**: 优化网络连接数据显示

### 🐛 问题修复
- **组件导入**: 修复缺失的Ant Design组件和图标导入
- **API错误**: 修复系统日志统计接口的500错误
- **空白页面**: 解决多个页面的空白显示问题

---

## [2025-01-XX] 核心功能实现

### 🛡️ 防火墙功能
- **nftables集成**: 完整的防火墙规则管理
- **实时应用**: 支持规则的实时添加、删除、修改
- **模式支持**: 黑名单和白名单两种工作模式
- **Docker兼容**: 确保与Docker网络配置兼容

### 📊 监控功能
- **系统监控**: CPU、内存、磁盘使用率监控
- **网络监控**: 网络连接状态和地理位置信息
- **进程监控**: 系统进程和Docker容器监控
- **日志管理**: 防火墙日志记录和查询

### 🔐 安全功能
- **Token管理**: 白名单访问Token的生成和管理
- **自助提交**: 通过Token自助提交白名单申请
- **权限控制**: 基于Token的访问控制机制

### 🎯 用户体验
- **响应式设计**: 适配不同屏幕尺寸
- **实时更新**: 关键数据的实时刷新
- **操作反馈**: 完善的操作成功/失败提示
- **数据可视化**: 直观的图表和进度条显示
