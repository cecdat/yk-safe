from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
import secrets
import string
from datetime import datetime, timedelta, timezone

from app.db.database import get_db
from app.db.models import WhitelistToken, WhitelistRequest, FirewallRule
from app.schemas.whitelist import (
    WhitelistTokenCreate, WhitelistTokenUpdate, WhitelistTokenResponse,
    WhitelistRequestCreate, WhitelistRequestResponse, WhitelistRequestUpdate,
    PublicWhitelistRequest, PublicWhitelistResponse
)
from app.schemas.token import TokenValidationRequest, TokenValidationResponse
from app.utils.ip_utils import get_client_ip, detect_proxy, get_public_ip, is_private_ip
from app.utils.firewall import reload_nftables
from app.utils.token_utils import validate_token_format, hash_token, verify_token
from app.utils.geo_utils import get_ip_location_simple

router = APIRouter()


def generate_token(length: int = 32) -> str:
    """生成随机token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_utc_now():
    """获取UTC当前时间"""
    return datetime.now(timezone.utc)


@router.post("/tokens", response_model=WhitelistTokenResponse)
def create_whitelist_token(
    token_data: WhitelistTokenCreate,
    db: Session = Depends(get_db)
):
    """创建白名单token"""
    # 生成唯一token
    while True:
        token = generate_token()
        if not db.query(WhitelistToken).filter(WhitelistToken.token == token).first():
            break
    
    db_token = WhitelistToken(
        token=token,
        company_name=token_data.company_name,
        description=token_data.description,
        max_uses=token_data.max_uses,
        expires_at=token_data.expires_at,
        created_by=token_data.created_by
    )
    
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    
    return db_token


@router.get("/tokens", response_model=List[WhitelistTokenResponse])
def get_whitelist_tokens(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取所有白名单token"""
    tokens = db.query(WhitelistToken).offset(skip).limit(limit).all()
    return tokens


@router.get("/tokens/{token_id}", response_model=WhitelistTokenResponse)
def get_whitelist_token(token_id: int, db: Session = Depends(get_db)):
    """获取特定白名单token"""
    token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return token


@router.put("/tokens/{token_id}", response_model=WhitelistTokenResponse)
def update_whitelist_token(
    token_id: int,
    token_data: WhitelistTokenUpdate,
    db: Session = Depends(get_db)
):
    """更新白名单token"""
    token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    for field, value in token_data.dict(exclude_unset=True).items():
        setattr(token, field, value)
    
    db.commit()
    db.refresh(token)
    return token


@router.delete("/tokens/{token_id}")
def delete_whitelist_token(token_id: int, db: Session = Depends(get_db)):
    """删除白名单token"""
    token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    db.delete(token)
    db.commit()
    return {"message": "Token deleted successfully"}


@router.post("/public/request", response_model=PublicWhitelistResponse)
def create_public_whitelist_request(
    request_data: PublicWhitelistRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """公开的白名单申请接口"""
    # 验证token
    token = db.query(WhitelistToken).filter(
        WhitelistToken.token == request_data.token,
        WhitelistToken.is_active == True
    ).first()
    
    if not token:
        raise HTTPException(
            status_code=400,
            detail="无效的token或token已禁用"
        )
    

    
    # 检查使用次数
    if token.used_count >= token.max_uses:
        raise HTTPException(
            status_code=400,
            detail="token使用次数已达上限"
        )
    
    # 检查IP地址格式
    if is_private_ip(request_data.ip_address):
        raise HTTPException(
            status_code=400,
            detail="不支持私有IP地址"
        )
    
    # 获取客户端信息
    client_ip = get_client_ip(request)
    is_proxy, proxy_info = detect_proxy(request)
    user_agent = request.headers.get("User-Agent", "")
    
    # 创建白名单申请
    whitelist_request = WhitelistRequest(
        token_id=token.id,
        company_name=request_data.company_name,
        ip_address=request_data.ip_address,
        user_agent=user_agent,
        request_ip=client_ip,
        is_proxy=is_proxy,
        proxy_info=str(proxy_info) if proxy_info else None,
        status="pending"
    )
    
    db.add(whitelist_request)
    
    # 增加token使用次数
    token.used_count += 1
    
    db.commit()
    db.refresh(whitelist_request)
    
    return PublicWhitelistResponse(
        success=True,
        message="白名单申请提交成功，等待审核",
        request_id=whitelist_request.id,
        status="pending"
    )


@router.get("/requests", response_model=List[WhitelistRequestResponse])
def get_whitelist_requests(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: Session = Depends(get_db)
):
    """获取白名单申请列表"""
    query = db.query(WhitelistRequest)
    if status:
        query = query.filter(WhitelistRequest.status == status)
    
    requests = query.offset(skip).limit(limit).all()
    return requests


@router.get("/requests/{request_id}", response_model=WhitelistRequestResponse)
def get_whitelist_request(request_id: int, db: Session = Depends(get_db)):
    """获取特定白名单申请"""
    request = db.query(WhitelistRequest).filter(WhitelistRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@router.put("/requests/{request_id}/approve")
def approve_whitelist_request(
    request_id: int,
    request_data: WhitelistRequestUpdate,
    db: Session = Depends(get_db)
):
    """审批白名单申请"""
    whitelist_request = db.query(WhitelistRequest).filter(
        WhitelistRequest.id == request_id
    ).first()
    
    if not whitelist_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if whitelist_request.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    # 更新申请状态
    whitelist_request.status = request_data.status
    whitelist_request.approved_by = request_data.approved_by
    whitelist_request.notes = request_data.notes
    
    if request_data.status == "approved":
        whitelist_request.approved_at = get_utc_now()
        
        # 创建防火墙规则
        firewall_rule = FirewallRule(
            rule_name=f"白名单-{whitelist_request.company_name}-{whitelist_request.ip_address}",
            protocol="tcp",
            source=whitelist_request.ip_address,
            destination="0.0.0.0/0",
            port="",
            action="accept",
            rule_type="input",
            description=f"自动生成的白名单规则 - {whitelist_request.company_name}",
            source_type="self_service",
            is_active=True
        )
        
        db.add(firewall_rule)
        
        # 重新加载防火墙
        reload_nftables(db)
    
    db.commit()
    
    return {
        "message": f"Request {request_data.status} successfully",
        "request_id": request_id,
        "status": request_data.status
    }


@router.get("/public/ip")
def get_public_ip_endpoint(request: Request):
    """获取访问者的公网IP地址"""
    try:
        print("[DEBUG] 开始获取访问者IP...")
        # 直接从请求中获取客户端IP
        client_ip = get_client_ip(request)
        print(f"[DEBUG] 获取到客户端IP: {client_ip}")
        
        if client_ip and not is_private_ip(client_ip):
            print(f"[DEBUG] 成功获取访问者公网IP: {client_ip}")
            return {"ip": client_ip}
        else:
            print(f"[DEBUG] 获取到私有IP或无效IP: {client_ip}")
            # 如果获取不到或获取到的是私有地址，给出提示
            return {"ip": "0.0.0.0", "note": "无法自动检测您的公网IP，请手动输入"}
    except Exception as e:
        print(f"[DEBUG] 获取访问者IP异常: {e}")
        # 确保异常情况下也返回明确的默认值
        return {"ip": "0.0.0.0", "note": "请手动输入您的公网IP地址"}


@router.get("/public/proxy-check")
def check_proxy(request: Request):
    """检查代理状态"""
    is_proxy, proxy_info = detect_proxy(request)
    return {
        "is_proxy": is_proxy,
        "proxy_info": proxy_info
    }


@router.post("/public/validate-token", response_model=TokenValidationResponse)
def validate_token(request_data: TokenValidationRequest, db: Session = Depends(get_db)):
    """验证token是否有效且支持自动审批"""
    # 验证token格式
    if not validate_token_format(request_data.token):
        return TokenValidationResponse(
            valid=False, 
            auto_approve=False, 
            message="Token格式无效"
        )
    
    # 查找token
    token = db.query(WhitelistToken).filter(
        WhitelistToken.token == request_data.token,
        WhitelistToken.is_active == True
    ).first()

    if not token:
        return TokenValidationResponse(
            valid=False, 
            auto_approve=False, 
            message="无效的token或token已禁用"
        )



    if token.used_count >= token.max_uses:
        return TokenValidationResponse(
            valid=False, 
            auto_approve=False, 
            message="Token使用次数已达上限"
        )

    return TokenValidationResponse(
        valid=True,
        auto_approve=token.auto_approve,
        message="Token有效",
        token_info=token
    )


@router.post("/public/auto-approve")
def auto_approve_whitelist(request_data: PublicWhitelistRequest, request: Request, db: Session = Depends(get_db)):
    """自动审批白名单申请"""
    # 验证token
    token = db.query(WhitelistToken).filter(
        WhitelistToken.token == request_data.token,
        WhitelistToken.is_active == True,
        WhitelistToken.auto_approve == True
    ).first()

    if not token:
        raise HTTPException(status_code=400, detail="无效的token或token不支持自动审批")



    # 检查使用次数
    if token.used_count >= token.max_uses:
        raise HTTPException(status_code=400, detail="token使用次数已达上限")

    # 检查IP地址格式
    if is_private_ip(request_data.ip_address):
        raise HTTPException(status_code=400, detail="不支持私有IP地址")

    # 获取客户端信息
    client_ip = get_client_ip(request)
    is_proxy, proxy_info = detect_proxy(request)
    user_agent = request.headers.get("User-Agent", "")

    # 创建白名单申请记录
    whitelist_request = WhitelistRequest(
        token_id=token.id,
        company_name=request_data.company_name,
        ip_address=request_data.ip_address,
        user_agent=user_agent,
        request_ip=client_ip,
        is_proxy=is_proxy,
        proxy_info=str(proxy_info) if proxy_info else None,
        status="approved",
        approved_at=get_utc_now(),
        approved_by="auto_approve",
        notes="自动审批通过"
    )

    db.add(whitelist_request)

    # 创建防火墙规则
    firewall_rule = FirewallRule(
        rule_name=f"白名单-{request_data.company_name}-{request_data.ip_address}",
        protocol="tcp",
        source=request_data.ip_address,
        destination="0.0.0.0/0",
        port="",
        action="accept",
        rule_type="input",
        description=f"自动生成的白名单规则 - {request_data.company_name}",
        source_type="self_service",
        is_active=True
    )

    db.add(firewall_rule)

    # 增加token使用次数
    token.used_count += 1

    # 重新加载防火墙
    reload_nftables(db)

    db.commit()

    return PublicWhitelistResponse(
        success=True,
        message="白名单自动添加成功",
        request_id=whitelist_request.id,
        status="approved"
    )

@router.post("/public/ip-location")
def get_ip_location_info(request_data: dict):
    """获取IP地址的地理位置信息"""
    try:
        ip_address = request_data.get("ip")
        if not ip_address:
            raise HTTPException(status_code=400, detail="IP地址不能为空")
        
        # 检查IP地址格式
        if is_private_ip(ip_address):
            return {
                "success": True,
                "ip": ip_address,
                "location": {
                    "country": "本地",
                    "city": "本地网络",
                    "region": "本地",
                    "timezone": "本地"
                }
            }
        
        # 获取地理位置信息
        location_info = get_ip_location_simple(ip_address)
        
        if location_info:
            return {
                "success": True,
                "ip": ip_address,
                "location": location_info
            }
        else:
            return {
                "success": True,
                "ip": ip_address,
                "location": {
                    "country": "未知",
                    "city": "未知",
                    "region": "未知",
                    "timezone": "未知"
                }
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"获取IP位置信息失败: {str(e)}",
            "ip": request_data.get("ip", ""),
            "location": None
        }
