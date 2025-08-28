from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import firewall, blacklist, monitor, logs, auth, whitelist, tokens, token_audit
from app.core.config import settings
from app.db.database import engine
from app.db import models

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="YK-Safe 防火墙管理系统",
    description="基于FastAPI的防火墙管理系统API",
    version="1.0.0"
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

@app.get("/")
async def root():
    return {"message": "YK-Safe 防火墙管理系统 API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
