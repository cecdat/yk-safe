from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, timezone
import re


class TokenCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=100, description="公司名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    max_uses: int = Field(100, ge=1, le=10000, description="最大使用次数")
    is_active: bool = Field(True, description="是否激活")
    auto_approve: bool = Field(True, description="是否自动审批")  # 默认设为True
    token_length: Optional[int] = Field(32, ge=16, le=64, description="token长度")
    
    @validator('company_name')
    def validate_company_name(cls, v):
        if not v.strip():
            raise ValueError('公司名称不能为空')
        return v.strip()


class TokenBulkCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=100, description="公司名称前缀")
    count: int = Field(..., ge=1, le=100, description="创建数量")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    max_uses: int = Field(100, ge=1, le=10000, description="最大使用次数")
    is_active: bool = Field(True, description="是否激活")
    auto_approve: bool = Field(True, description="是否自动审批")  # 默认设为True
    token_length: Optional[int] = Field(32, ge=16, le=64, description="token长度")
    
    @validator('company_name')
    def validate_company_name(cls, v):
        if not v.strip():
            raise ValueError('公司名称不能为空')
        return v.strip()


class TokenUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=100, description="公司名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    max_uses: Optional[int] = Field(None, ge=1, le=10000, description="最大使用次数")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    is_active: Optional[bool] = Field(None, description="是否激活")
    auto_approve: Optional[bool] = Field(None, description="是否自动审批")
    
    @validator('company_name')
    def validate_company_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('公司名称不能为空')
        return v.strip() if v else v
    
    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v is not None:
            # 确保比较的是timezone-aware datetime
            now = datetime.now(timezone.utc)
            if v.tzinfo is None:
                # 如果输入的是naive datetime，假设是UTC
                v = v.replace(tzinfo=timezone.utc)
            if v <= now:
                raise ValueError('过期时间必须大于当前时间')
        return v


class TokenResponse(BaseModel):
    id: int
    token: str
    company_name: str
    description: Optional[str]
    max_uses: int
    used_count: int
    expires_at: Optional[datetime]
    is_active: bool
    auto_approve: bool
    created_at: datetime
    created_by: Optional[str]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TokenListResponse(BaseModel):
    tokens: List[TokenResponse]
    total: int
    skip: int
    limit: int
    
    class Config:
        from_attributes = True


class TokenUsageResponse(BaseModel):
    token_id: int
    total_requests: int
    approved_requests: int
    pending_requests: int
    rejected_requests: int
    used_count: int
    max_uses: int
    usage_rate: float
    is_expired: bool
    is_active: bool
    
    class Config:
        from_attributes = True


class TokenStatsResponse(BaseModel):
    total_tokens: int
    active_tokens: int
    expired_tokens: int
    auto_approve_tokens: int
    today_tokens: int
    total_requests: int
    pending_requests: int
    
    class Config:
        from_attributes = True


class TokenValidationRequest(BaseModel):
    token: str = Field(..., min_length=16, description="要验证的token")
    
    @validator('token')
    def validate_token_format(cls, v):
        if len(v) < 16:
            raise ValueError('Token长度不能少于16位')
        # 检查是否包含字母和数字
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError('Token必须包含字母和数字')
        return v


class TokenValidationResponse(BaseModel):
    valid: bool
    auto_approve: bool
    message: str
    token_info: Optional[TokenResponse] = None
    
    class Config:
        from_attributes = True


class TokenExportRequest(BaseModel):
    format: str = Field("json", pattern="^(json|csv|excel)$", description="导出格式")
    include_inactive: bool = Field(False, description="是否包含非活跃token")
    include_expired: bool = Field(False, description="是否包含过期token")
    company_filter: Optional[str] = Field(None, description="公司名称过滤")
    
    class Config:
        from_attributes = True


class TokenImportRequest(BaseModel):
    tokens: List[TokenCreate]
    overwrite_existing: bool = Field(False, description="是否覆盖已存在的token")
    
    class Config:
        from_attributes = True


class TokenImportResponse(BaseModel):
    success_count: int
    failed_count: int
    errors: List[str]
    
    class Config:
        from_attributes = True


class TokenAuditLog(BaseModel):
    id: int
    token_id: int
    action: str  # create, update, delete, activate, deactivate, regenerate
    user: str
    details: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenAuditLogResponse(BaseModel):
    logs: List[TokenAuditLog]
    total: int
    skip: int
    limit: int
    
    class Config:
        from_attributes = True
