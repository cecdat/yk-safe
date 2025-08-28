from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BlacklistIP(Base):
    __tablename__ = "blacklist_ips"
    
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, unique=True, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

class FirewallRule(Base):
    __tablename__ = "firewall_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String, unique=True, index=True)
    protocol = Column(String)  # tcp, udp, icmp
    source = Column(String)  # 源地址
    destination = Column(String)  # 目标地址
    port = Column(String)  # 端口
    action = Column(String)  # accept, drop
    rule_type = Column(String)  # input, output, forward
    description = Column(Text)  # 规则描述
    source_type = Column(String, default="manual")  # manual, self_service, system
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String)  # info, warning, error
    message = Column(Text)
    source = Column(String)  # firewall, blacklist, system
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FirewallLog(Base):
    __tablename__ = "firewall_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    source_ip = Column(String, index=True)
    destination_ip = Column(String, index=True)
    protocol = Column(String, index=True)  # tcp, udp, icmp, all
    source_port = Column(Integer, index=True)
    destination_port = Column(Integer, index=True)
    action = Column(String, index=True)  # drop, accept, reject
    rule_id = Column(Integer, ForeignKey("firewall_rules.id"), nullable=True)  # 关联的规则ID
    rule_name = Column(String, nullable=True)  # 规则名称
    interface = Column(String, nullable=True)  # 网络接口
    packet_size = Column(Integer, nullable=True)  # 数据包大小
    tcp_flags = Column(String, nullable=True)  # TCP标志
    country = Column(String, nullable=True)  # 源IP国家
    city = Column(String, nullable=True)  # 源IP城市
    isp = Column(String, nullable=True)  # 网络服务商
    threat_level = Column(String, default="low")  # 威胁等级: low, medium, high, critical
    description = Column(Text, nullable=True)  # 详细描述
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class FirewallConfig(Base):
    __tablename__ = "firewall_config"
    
    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String, default="blacklist")  # blacklist, whitelist
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String)


class WhitelistToken(Base):
    __tablename__ = "whitelist_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    company_name = Column(String, nullable=False)
    description = Column(Text)
    max_uses = Column(Integer, default=100)  # 最大使用次数
    used_count = Column(Integer, default=0)  # 已使用次数
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 过期时间
    is_active = Column(Boolean, default=True)  # 是否激活
    auto_approve = Column(Boolean, default=False)  # 是否自动审批
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WhitelistRequest(Base):
    __tablename__ = "whitelist_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("whitelist_tokens.id"))
    company_name = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    user_agent = Column(Text)
    request_ip = Column(String)  # 请求来源IP
    is_proxy = Column(Boolean, default=False)  # 是否代理
    proxy_info = Column(Text)  # 代理信息
    status = Column(String, default="pending")  # pending, approved, rejected
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)


class TokenAuditLog(Base):
    __tablename__ = "token_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("whitelist_tokens.id"))
    action = Column(String, nullable=False)  # create, update, delete, activate, deactivate, regenerate
    user = Column(String, nullable=False)
    details = Column(Text)  # 详细操作信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
