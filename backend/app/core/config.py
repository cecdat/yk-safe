from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # 数据库配置 - 使用绝对路径
    database_url: str = "sqlite:////opt/yk-safe/backend/yk_safe.db"
    
    # JWT配置
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 防火墙配置
    nftables_config_path: str = "/etc/nftables.conf"
    nft_command_path: str = "/usr/sbin/nft"
    
    # 应用配置
    app_name: str = "YK-Safe"
    debug: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()
