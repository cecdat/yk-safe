from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
import re


class WhitelistTokenCreate(BaseModel):
    company_name: str
    description: Optional[str] = None
    max_uses: int = 100
    expires_at: datetime
    is_active: bool = True
    auto_approve: bool = False
    created_by: Optional[str] = None


class WhitelistTokenUpdate(BaseModel):
    company_name: Optional[str] = None
    description: Optional[str] = None
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    auto_approve: Optional[bool] = None
    is_active: Optional[bool] = None


class WhitelistTokenResponse(BaseModel):
    id: int
    token: str
    company_name: str
    description: Optional[str]
    max_uses: int
    used_count: int
    expires_at: datetime
    is_active: bool
    created_at: datetime
    created_by: Optional[str]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class WhitelistRequestCreate(BaseModel):
    token: str
    company_name: str
    ip_address: str
    user_agent: Optional[str] = None
    
    @validator('ip_address')
    def validate_ip_address(cls, v):
        # 简单的IP地址验证
        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if not re.match(ip_pattern, v):
            raise ValueError('无效的IP地址格式')
        return v


class WhitelistRequestResponse(BaseModel):
    id: int
    token_id: int
    company_name: str
    ip_address: str
    user_agent: Optional[str]
    request_ip: Optional[str]
    is_proxy: bool
    proxy_info: Optional[str]
    status: str
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    created_at: datetime
    notes: Optional[str]
    
    class Config:
        from_attributes = True


class WhitelistRequestUpdate(BaseModel):
    status: str
    approved_by: Optional[str] = None
    notes: Optional[str] = None


class PublicWhitelistRequest(BaseModel):
    company_name: str
    ip_address: str
    token: str


class PublicWhitelistResponse(BaseModel):
    success: bool
    message: str
    request_id: Optional[int] = None
    status: Optional[str] = None
