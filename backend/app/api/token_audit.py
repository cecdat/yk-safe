from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.db.database import get_db
from app.db.models import TokenAuditLog, WhitelistToken, User
from app.schemas.token import TokenAuditLogResponse
from app.utils.auth import get_current_user
from app.utils.token_utils import log_token_action

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=TokenAuditLogResponse)
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    token_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """获取token审计日志"""
    try:
        query = db.query(TokenAuditLog)
        
        # 应用过滤条件
        if token_id:
            query = query.filter(TokenAuditLog.token_id == token_id)
        
        if action:
            query = query.filter(TokenAuditLog.action == action)
        
        if user:
            query = query.filter(TokenAuditLog.user.ilike(f"%{user}%"))
        
        if start_date:
            query = query.filter(TokenAuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(TokenAuditLog.created_at <= end_date)
        
        # 获取总数
        total = query.count()
        
        # 分页并按时间倒序排列
        logs = query.order_by(desc(TokenAuditLog.created_at)).offset(skip).limit(limit).all()
        
        return TokenAuditLogResponse(
            logs=logs,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"获取审计日志失败: {e}")
        raise HTTPException(status_code=500, detail="获取审计日志失败")


@router.get("/token/{token_id}", response_model=TokenAuditLogResponse)
def get_token_audit_logs(
    token_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取特定token的审计日志"""
    try:
        # 验证token是否存在
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if not token:
            raise HTTPException(status_code=404, detail="Token不存在")
        
        query = db.query(TokenAuditLog).filter(TokenAuditLog.token_id == token_id)
        
        # 获取总数
        total = query.count()
        
        # 分页并按时间倒序排列
        logs = query.order_by(desc(TokenAuditLog.created_at)).offset(skip).limit(limit).all()
        
        return TokenAuditLogResponse(
            logs=logs,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取token审计日志失败: {e}")
        raise HTTPException(status_code=500, detail="获取token审计日志失败")


@router.get("/actions/summary")
def get_audit_actions_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """获取审计操作统计摘要"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 获取指定时间范围内的日志
        logs = db.query(TokenAuditLog).filter(
            TokenAuditLog.created_at >= start_date
        ).all()
        
        # 按操作类型统计
        action_counts = {}
        user_counts = {}
        daily_counts = {}
        
        for log in logs:
            # 操作类型统计
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
            
            # 用户统计
            user_counts[log.user] = user_counts.get(log.user, 0) + 1
            
            # 每日统计
            date_key = log.created_at.date().isoformat()
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        # 获取最活跃的用户
        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 获取最常用的操作
        top_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "period_days": days,
            "total_logs": len(logs),
            "action_distribution": action_counts,
            "user_activity": {
                "top_users": top_users,
                "unique_users": len(user_counts)
            },
            "daily_activity": {
                "daily_counts": daily_counts,
                "average_daily": round(len(logs) / days, 2) if days > 0 else 0
            },
            "most_common_actions": top_actions
        }
        
    except Exception as e:
        logger.error(f"获取审计操作统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取审计操作统计失败")


@router.get("/export")
def export_audit_logs(
    format: str = Query("csv", pattern="^(csv|json)$"),
    token_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """导出审计日志"""
    try:
        query = db.query(TokenAuditLog)
        
        # 应用过滤条件
        if token_id:
            query = query.filter(TokenAuditLog.token_id == token_id)
        
        if action:
            query = query.filter(TokenAuditLog.action == action)
        
        if user:
            query = query.filter(TokenAuditLog.user.ilike(f"%{user}%"))
        
        if start_date:
            query = query.filter(TokenAuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(TokenAuditLog.created_at <= end_date)
        
        logs = query.order_by(desc(TokenAuditLog.created_at)).all()
        
        if format == "csv":
            return export_logs_to_csv(logs, db)
        else:
            return export_logs_to_json(logs, db)
        
    except Exception as e:
        logger.error(f"导出审计日志失败: {e}")
        raise HTTPException(status_code=500, detail="导出审计日志失败")


def export_logs_to_csv(logs: List[TokenAuditLog], db: Session) -> str:
    """将审计日志导出为CSV格式"""
    try:
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            'ID', 'Token ID', '公司名称', '操作', '用户', '详细信息', '操作时间'
        ])
        
        # 写入数据
        for log in logs:
            # 获取token信息
            token = db.query(WhitelistToken).filter(WhitelistToken.id == log.token_id).first()
            company_name = token.company_name if token else "未知"
            
            writer.writerow([
                log.id,
                log.token_id,
                company_name,
                log.action,
                log.user,
                log.details or '',
                log.created_at.isoformat()
            ])
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"导出审计日志到CSV失败: {e}")
        return ""


def export_logs_to_json(logs: List[TokenAuditLog], db: Session) -> dict:
    """将审计日志导出为JSON格式"""
    try:
        result = []
        
        for log in logs:
            # 获取token信息
            token = db.query(WhitelistToken).filter(WhitelistToken.id == log.token_id).first()
            
            log_data = {
                "id": log.id,
                "token_id": log.token_id,
                "company_name": token.company_name if token else "未知",
                "action": log.action,
                "user": log.user,
                "details": log.details,
                "created_at": log.created_at.isoformat()
            }
            result.append(log_data)
        
        return {
            "total": len(result),
            "logs": result,
            "export_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"导出审计日志到JSON失败: {e}")
        return {"error": "导出失败"}


@router.delete("/cleanup")
def cleanup_old_audit_logs(
    days: int = Query(90, ge=30, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清理旧的审计日志"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 查找要删除的日志
        old_logs = db.query(TokenAuditLog).filter(
            TokenAuditLog.created_at < cutoff_date
        ).all()
        
        deleted_count = len(old_logs)
        
        if deleted_count > 0:
            # 删除旧日志
            for log in old_logs:
                db.delete(log)
            
            db.commit()
            
            # 记录清理操作
            log_token_action(
                token_id=0,  # 系统操作
                action="cleanup_audit_logs",
                user=current_user.username,
                details=f"清理了 {deleted_count} 条 {days} 天前的审计日志",
                db=db
            )
            
            logger.info(f"用户 {current_user.username} 清理了 {deleted_count} 条审计日志")
        
        return {
            "message": f"成功清理了 {deleted_count} 条 {days} 天前的审计日志",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"清理审计日志失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="清理审计日志失败")


@router.get("/recent")
def get_recent_audit_logs(
    hours: int = Query(24, ge=1, le=168),  # 最多7天
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """获取最近的审计日志"""
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        logs = db.query(TokenAuditLog).filter(
            TokenAuditLog.created_at >= start_time
        ).order_by(desc(TokenAuditLog.created_at)).limit(limit).all()
        
        # 获取相关的token信息
        token_ids = list(set(log.token_id for log in logs))
        tokens = db.query(WhitelistToken).filter(WhitelistToken.id.in_(token_ids)).all()
        token_map = {token.id: token for token in tokens}
        
        result = []
        for log in logs:
            token = token_map.get(log.token_id)
            log_data = {
                "id": log.id,
                "token_id": log.token_id,
                "company_name": token.company_name if token else "未知",
                "action": log.action,
                "user": log.user,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
                "time_ago": get_time_ago(log.created_at)
            }
            result.append(log_data)
        
        return {
            "period_hours": hours,
            "total_logs": len(result),
            "logs": result
        }
        
    except Exception as e:
        logger.error(f"获取最近审计日志失败: {e}")
        raise HTTPException(status_code=500, detail="获取最近审计日志失败")


def get_time_ago(created_at: datetime) -> str:
    """计算相对时间"""
    now = datetime.utcnow()
    diff = now - created_at
    
    if diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"
