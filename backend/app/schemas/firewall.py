from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class BlacklistIPCreate(BaseModel):
    ip_address: str
    description: Optional[str] = None

class BlacklistIPResponse(BaseModel):
    id: int
    ip_address: str
    description: Optional[str]
    created_at: datetime
    is_active: bool

class FirewallRuleCreate(BaseModel):
    rule_name: str
    protocol: str
    source: str
    destination: str
    port: Optional[str] = None
    action: str
    rule_type: str
    description: Optional[str] = None
    source_type: Optional[str] = "manual"
    is_active: Optional[bool] = True
    apply_immediately: Optional[bool] = True

class FirewallRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    protocol: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    port: Optional[str] = None
    action: Optional[str] = None
    rule_type: Optional[str] = None
    description: Optional[str] = None
    source_type: Optional[str] = None
    is_active: Optional[bool] = None
    apply_immediately: Optional[bool] = True

class FirewallRuleResponse(BaseModel):
    id: int
    rule_name: str
    protocol: str
    source: str
    destination: str
    port: Optional[str]
    action: str
    rule_type: str
    description: Optional[str]
    source_type: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

class FirewallStatus(BaseModel):
    is_running: bool
    rules_count: int
    blacklist_count: int
    last_updated: datetime

class FirewallLogResponse(BaseModel):
    id: int
    source_ip: str
    destination_ip: str
    protocol: str
    port: int
    action: str
    timestamp: datetime

class FirewallConfigResponse(BaseModel):
    id: int
    mode: str
    description: Optional[str]
    updated_at: Optional[datetime]
    updated_by: Optional[str]

class FirewallModeUpdate(BaseModel):
    mode: str
    description: Optional[str] = None
