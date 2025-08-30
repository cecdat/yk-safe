from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import firewall, blacklist, monitor, logs, auth, whitelist, tokens, token_audit, network, settings as settings_api
from app.core.config import settings
from app.db.database import engine
from app.db import models

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

# 定义 OpenAPI 信息
openapi_info = {
    "title": "YK-Safe 防火墙管理系统",
    "description": """
    ## YK-Safe 防火墙管理系统 API
    
    基于 FastAPI 的现代化防火墙管理系统，提供以下功能：
    
    ### 核心功能
    - **防火墙管理**: 支持黑名单/白名单模式切换
    - **规则管理**: 添加、编辑、删除防火墙规则
    - **系统监控**: 实时监控系统资源
    - **日志管理**: 查看和管理系统日志
    - **用户认证**: JWT 认证系统
    
    ### 白名单功能
    - **Token管理**: 支持Token创建和管理
    - **申请审核**: 完整的申请审核流程
    - **自动规则创建**: 审核通过后自动创建防火墙规则
    
    ### 网络工具
    - **tcpdump**: 网络抓包工具
    - **ping**: 网络连通性测试
    - **traceroute**: 路由追踪
    
    ### 系统设置
    - **密码修改**: 用户密码管理
    - **数据备份**: 系统数据备份和恢复
    - **推送设置**: 支持多种推送渠道
    """,
    "version": "1.0.0",
    "contact": {
        "name": "YK-Safe Support",
        "email": "support@yk-safe.com"
    },
    "license_info": {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
}

app = FastAPI(
    **openapi_info,
    openapi_version="3.0.2",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[
        {"url": "http://localhost:5023", "description": "本地开发环境"},
        {"url": "http://120.226.208.2:5023", "description": "生产环境"}
    ]
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(firewall.router, prefix="/api/firewall", tags=["防火墙"])
app.include_router(blacklist.router, prefix="/api/blacklist", tags=["黑名单"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["监控"])
app.include_router(logs.router, prefix="/api/logs", tags=["日志"])
app.include_router(whitelist.router, prefix="/api/whitelist", tags=["白名单"])
app.include_router(tokens.router, prefix="/api/tokens", tags=["Token管理"])
app.include_router(token_audit.router, prefix="/api/token-audit", tags=["Token审计"])
app.include_router(network.router, prefix="/api/network", tags=["网络工具"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["系统设置"])

@app.get("/", tags=["根路径"])
async def root():
    """系统根路径，返回系统信息"""
    return {
        "message": "YK-Safe 防火墙管理系统 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", tags=["健康检查"])
async def health_check():
    """系统健康检查接口"""
    return {"status": "healthy", "timestamp": "2024-12-19T00:00:00Z"}
