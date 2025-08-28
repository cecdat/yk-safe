from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import secrets
import string
from datetime import datetime, timedelta, timezone
import logging

from app.db.database import get_db
from app.db.models import WhitelistToken, WhitelistRequest, User
from app.schemas.token import (
    TokenCreate, TokenUpdate, TokenResponse, TokenListResponse,
    TokenUsageResponse, TokenStatsResponse, TokenBulkCreate
)
from app.utils.auth import get_current_user

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()


def generate_secure_token(length: int = 32) -> str:
    """生成安全的随机token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_token_format(token: str) -> bool:
    """验证token格式"""
    if len(token) < 16:
        return False
    # 检查是否包含字母和数字
    has_letter = any(c.isalpha() for c in token)
    has_digit = any(c.isdigit() for c in token)
    return has_letter and has_digit


def get_utc_now():
    """获取UTC当前时间"""
    return datetime.now(timezone.utc)


@router.post("/", response_model=TokenResponse)
def create_token(
    token_data: TokenCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的token"""
    try:
        # 生成唯一token
        attempts = 0
        while attempts < 10:
            token = generate_secure_token(token_data.token_length or 32)
            if not db.query(WhitelistToken).filter(WhitelistToken.token == token).first():
                break
            attempts += 1
        else:
            raise HTTPException(status_code=500, detail="无法生成唯一token")
        
        # 创建token记录
        db_token = WhitelistToken(
            token=token,
            company_name=token_data.company_name,
            description=token_data.description,
            max_uses=token_data.max_uses,
            expires_at=None,  # 不再设置过期时间
            is_active=token_data.is_active,
            auto_approve=token_data.auto_approve,
            created_by=current_user.username
        )
        
        db.add(db_token)
        db.commit()
        db.refresh(db_token)
        
        logger.info(f"用户 {current_user.username} 创建了token: {token_data.company_name}")
        return db_token
        
    except Exception as e:
        logger.error(f"创建token失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="创建token失败")


@router.post("/bulk", response_model=List[TokenResponse])
def create_bulk_tokens(
    bulk_data: TokenBulkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量创建token"""
    try:
        created_tokens = []
        
        for i in range(bulk_data.count):
            # 生成唯一token
            attempts = 0
            while attempts < 10:
                token = generate_secure_token(bulk_data.token_length or 32)
                if not db.query(WhitelistToken).filter(WhitelistToken.token == token).first():
                    break
                attempts += 1
            else:
                raise HTTPException(status_code=500, detail=f"无法生成第{i+1}个唯一token")
            
            # 创建token记录
            db_token = WhitelistToken(
                token=token,
                company_name=f"{bulk_data.company_name}_{i+1}",
                description=bulk_data.description,
                max_uses=bulk_data.max_uses,
                expires_at=None,  # 不再设置过期时间
                is_active=bulk_data.is_active,
                auto_approve=bulk_data.auto_approve,
                created_by=current_user.username
            )
            
            db.add(db_token)
            created_tokens.append(db_token)
        
        db.commit()
        
        # 刷新所有创建的token
        for token in created_tokens:
            db.refresh(token)
        
        logger.info(f"用户 {current_user.username} 批量创建了 {bulk_data.count} 个token")
        return created_tokens
        
    except Exception as e:
        logger.error(f"批量创建token失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="批量创建token失败")


@router.get("/", response_model=TokenListResponse)
def list_tokens(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    company_name: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    auto_approve: Optional[bool] = Query(None),
    expired: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """获取token列表，支持多种过滤条件"""
    try:
        query = db.query(WhitelistToken)
        
        # 应用过滤条件
        if company_name:
            query = query.filter(WhitelistToken.company_name.ilike(f"%{company_name}%"))
        
        if is_active is not None:
            query = query.filter(WhitelistToken.is_active == is_active)
        
        if auto_approve is not None:
            query = query.filter(WhitelistToken.auto_approve == auto_approve)
        

        
        # 获取总数
        total = query.count()
        
        # 分页
        tokens = query.order_by(WhitelistToken.created_at.desc()).offset(skip).limit(limit).all()
        
        return TokenListResponse(
            tokens=tokens,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"获取token列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取token列表失败")


@router.get("/{token_id}", response_model=TokenResponse)
def get_token(token_id: int, db: Session = Depends(get_db)):
    """获取特定token详情"""
    try:
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if not token:
            raise HTTPException(status_code=404, detail="Token不存在")
        
        return token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取token详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取token详情失败")


@router.put("/{token_id}", response_model=TokenResponse)
def update_token(
    token_id: int,
    token_data: TokenUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新token"""
    try:
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if not token:
            raise HTTPException(status_code=404, detail="Token不存在")
        
        # 更新字段
        update_data = token_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(token, field, value)
        
        db.commit()
        db.refresh(token)
        
        logger.info(f"用户 {current_user.username} 更新了token {token_id}")
        return token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新token失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="更新token失败")


@router.delete("/{token_id}")
def delete_token(
    token_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除token"""
    try:
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if not token:
            raise HTTPException(status_code=404, detail="Token不存在")
        
        # 检查是否有未处理的请求
        pending_requests = db.query(WhitelistRequest).filter(
            and_(
                WhitelistRequest.token_id == token_id,
                WhitelistRequest.status == "pending"
            )
        ).count()
        
        if pending_requests > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"无法删除token，还有 {pending_requests} 个待处理的请求"
            )
        
        db.delete(token)
        db.commit()
        
        logger.info(f"用户 {current_user.username} 删除了token {token_id}")
        return {"message": "Token删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除token失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="删除token失败")


@router.post("/{token_id}/activate")
def activate_token(
    token_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """激活token"""
    try:
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if not token:
            raise HTTPException(status_code=404, detail="Token不存在")
        
        token.is_active = True
        db.commit()
        
        logger.info(f"用户 {current_user.username} 激活了token {token_id}")
        return {"message": "Token激活成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活token失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="激活token失败")


@router.post("/{token_id}/deactivate")
def deactivate_token(
    token_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """停用token"""
    try:
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if not token:
            raise HTTPException(status_code=404, detail="Token不存在")
        
        token.is_active = False
        db.commit()
        
        logger.info(f"用户 {current_user.username} 停用了token {token_id}")
        return {"message": "Token停用成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停用token失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="停用token失败")


@router.get("/{token_id}/usage", response_model=TokenUsageResponse)
def get_token_usage(token_id: int, db: Session = Depends(get_db)):
    """获取token使用情况"""
    try:
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if not token:
            raise HTTPException(status_code=404, detail="Token不存在")
        
        # 获取相关请求统计
        total_requests = db.query(WhitelistRequest).filter(
            WhitelistRequest.token_id == token_id
        ).count()
        
        approved_requests = db.query(WhitelistRequest).filter(
            and_(
                WhitelistRequest.token_id == token_id,
                WhitelistRequest.status == "approved"
            )
        ).count()
        
        pending_requests = db.query(WhitelistRequest).filter(
            and_(
                WhitelistRequest.token_id == token_id,
                WhitelistRequest.status == "pending"
            )
        ).count()
        
        rejected_requests = db.query(WhitelistRequest).filter(
            and_(
                WhitelistRequest.token_id == token_id,
                WhitelistRequest.status == "rejected"
            )
        ).count()
        
        # 计算使用率
        usage_rate = (token.used_count / token.max_uses * 100) if token.max_uses > 0 else 0
        
        return TokenUsageResponse(
            token_id=token_id,
            total_requests=total_requests,
            approved_requests=approved_requests,
            pending_requests=pending_requests,
            rejected_requests=rejected_requests,
            used_count=token.used_count,
            max_uses=token.max_uses,
            usage_rate=round(usage_rate, 2),
            is_expired=False,  # 不再有过期时间
            is_active=token.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取token使用情况失败: {e}")
        raise HTTPException(status_code=500, detail="获取token使用情况失败")


@router.get("/stats/overview", response_model=TokenStatsResponse)
def get_token_stats(db: Session = Depends(get_db)):
    """获取token统计概览"""
    try:
        # 总token数
        total_tokens = db.query(WhitelistToken).count()
        
        # 活跃token数
        active_tokens = db.query(WhitelistToken).filter(WhitelistToken.is_active == True).count()
        
        # 过期token数（现在都是永久有效）
        expired_tokens = 0
        
        # 自动审批token数
        auto_approve_tokens = db.query(WhitelistToken).filter(
            WhitelistToken.auto_approve == True
        ).count()
        
        # 今日创建的token数
        today = get_utc_now().date()
        today_tokens = db.query(WhitelistToken).filter(
            WhitelistToken.created_at >= today
        ).count()
        
        # 总请求数
        total_requests = db.query(WhitelistRequest).count()
        
        # 待处理请求数
        pending_requests = db.query(WhitelistRequest).filter(
            WhitelistRequest.status == "pending"
        ).count()
        
        return TokenStatsResponse(
            total_tokens=total_tokens,
            active_tokens=active_tokens,
            expired_tokens=expired_tokens,
            auto_approve_tokens=auto_approve_tokens,
            today_tokens=today_tokens,
            total_requests=total_requests,
            pending_requests=pending_requests
        )
        
    except Exception as e:
        logger.error(f"获取token统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取token统计失败")


@router.post("/{token_id}/regenerate")
def regenerate_token(
    token_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重新生成token"""
    try:
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if not token:
            raise HTTPException(status_code=404, detail="Token不存在")
        
        # 生成新token
        attempts = 0
        while attempts < 10:
            new_token = generate_secure_token(len(token.token))
            if not db.query(WhitelistToken).filter(WhitelistToken.token == new_token).first():
                break
            attempts += 1
        else:
            raise HTTPException(status_code=500, detail="无法生成唯一token")
        
        old_token = token.token
        token.token = new_token
        db.commit()
        
        logger.info(f"用户 {current_user.username} 重新生成了token {token_id}: {old_token} -> {new_token}")
        return {"message": "Token重新生成成功", "new_token": new_token}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新生成token失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="重新生成token失败")
