import secrets
import string
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import WhitelistToken, WhitelistRequest, TokenAuditLog

# 配置日志
logger = logging.getLogger(__name__)


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


def hash_token(token: str) -> str:
    """对token进行哈希处理（用于安全存储）"""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(token: str, db: Session) -> Optional[WhitelistToken]:
    """验证token的有效性"""
    try:
        # 查找token
        db_token = db.query(WhitelistToken).filter(WhitelistToken.token == token).first()
        
        if not db_token:
            return None
        
        # 检查是否激活
        if not db_token.is_active:
            logger.warning(f"Token {token[:8]}... 已停用")
            return None
        

        
        # 检查使用次数
        if db_token.used_count >= db_token.max_uses:
            logger.warning(f"Token {token[:8]}... 已达到最大使用次数")
            return None
        
        return db_token
        
    except Exception as e:
        logger.error(f"验证token时出错: {e}")
        return None


def increment_token_usage(token_id: int, db: Session) -> bool:
    """增加token使用次数"""
    try:
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if token:
            token.used_count += 1
            db.commit()
            logger.info(f"Token {token_id} 使用次数增加到 {token.used_count}")
            return True
        return False
    except Exception as e:
        logger.error(f"增加token使用次数失败: {e}")
        db.rollback()
        return False


def log_token_action(
    token_id: int, 
    action: str, 
    user: str, 
    details: Optional[str] = None, 
    db: Session = None
) -> bool:
    """记录token操作日志"""
    try:
        if db is None:
            return False
        
        audit_log = TokenAuditLog(
            token_id=token_id,
            action=action,
            user=user,
            details=details
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info(f"记录token操作日志: {action} by {user} for token {token_id}")
        return True
        
    except Exception as e:
        logger.error(f"记录token操作日志失败: {e}")
        if db:
            db.rollback()
        return False


def get_token_statistics(db: Session) -> Dict[str, Any]:
    """获取token统计信息"""
    try:
        now = get_utc_now()
        
        # 基础统计
        total_tokens = db.query(WhitelistToken).count()
        active_tokens = db.query(WhitelistToken).filter(WhitelistToken.is_active == True).count()
        expired_tokens = db.query(WhitelistToken).filter(WhitelistToken.expires_at < now).count()
        auto_approve_tokens = db.query(WhitelistToken).filter(WhitelistToken.auto_approve == True).count()
        
        # 今日统计
        today = now.date()
        today_tokens = db.query(WhitelistToken).filter(
            WhitelistToken.created_at >= today
        ).count()
        
        # 请求统计
        total_requests = db.query(WhitelistRequest).count()
        pending_requests = db.query(WhitelistRequest).filter(
            WhitelistRequest.status == "pending"
        ).count()
        approved_requests = db.query(WhitelistRequest).filter(
            WhitelistRequest.status == "approved"
        ).count()
        rejected_requests = db.query(WhitelistRequest).filter(
            WhitelistRequest.status == "rejected"
        ).count()
        
        # 使用率统计
        high_usage_tokens = db.query(WhitelistToken).filter(
            and_(
                WhitelistToken.max_uses > 0,
                WhitelistToken.used_count >= WhitelistToken.max_uses * 0.8
            )
        ).count()
        
        return {
            "total_tokens": total_tokens,
            "active_tokens": active_tokens,
            "expired_tokens": expired_tokens,
            "auto_approve_tokens": auto_approve_tokens,
            "today_tokens": today_tokens,
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "high_usage_tokens": high_usage_tokens,
            "approval_rate": round(approved_requests / total_requests * 100, 2) if total_requests > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"获取token统计信息失败: {e}")
        return {}


def cleanup_expired_tokens(db: Session) -> int:
    """清理过期的token"""
    try:
        now = get_utc_now()
        
        # 查找过期的token
        expired_tokens = db.query(WhitelistToken).filter(
            and_(
                WhitelistToken.expires_at < now,
                WhitelistToken.is_active == True
            )
        ).all()
        
        cleaned_count = 0
        for token in expired_tokens:
            token.is_active = False
            cleaned_count += 1
        
        if cleaned_count > 0:
            db.commit()
            logger.info(f"清理了 {cleaned_count} 个过期token")
        
        return cleaned_count
        
    except Exception as e:
        logger.error(f"清理过期token失败: {e}")
        db.rollback()
        return 0


def get_token_usage_analytics(token_id: int, db: Session) -> Dict[str, Any]:
    """获取token使用分析"""
    try:
        token = db.query(WhitelistToken).filter(WhitelistToken.id == token_id).first()
        if not token:
            return {}
        
        # 获取相关请求
        requests = db.query(WhitelistRequest).filter(
            WhitelistRequest.token_id == token_id
        ).all()
        
        # 按状态统计
        status_counts = {}
        for req in requests:
            status_counts[req.status] = status_counts.get(req.status, 0) + 1
        
        # 按时间统计（最近30天）
        thirty_days_ago = get_utc_now() - timedelta(days=30)
        recent_requests = [req for req in requests if req.created_at >= thirty_days_ago]
        
        # 按IP统计
        ip_counts = {}
        for req in requests:
            ip_counts[req.ip_address] = ip_counts.get(req.ip_address, 0) + 1
        
        # 计算使用率
        usage_rate = (token.used_count / token.max_uses * 100) if token.max_uses > 0 else 0
        
        return {
            "token_info": {
                "id": token.id,
                "company_name": token.company_name,
                "used_count": token.used_count,
                "max_uses": token.max_uses,
                "usage_rate": round(usage_rate, 2),
                "is_expired": False,  # 不再有过期时间
                "is_active": token.is_active
            },
            "requests_summary": {
                "total": len(requests),
                "recent_30_days": len(recent_requests),
                "status_distribution": status_counts
            },
            "top_ips": sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "usage_trend": {
                            "daily_usage": len([req for req in recent_requests if req.created_at.date() == get_utc_now().date()]),
            "weekly_usage": len([req for req in recent_requests if req.created_at >= get_utc_now() - timedelta(days=7)]),
                "monthly_usage": len(recent_requests)
            }
        }
        
    except Exception as e:
        logger.error(f"获取token使用分析失败: {e}")
        return {}


def validate_bulk_token_creation(data: Dict[str, Any]) -> List[str]:
    """验证批量创建token的数据"""
    errors = []
    
    # 检查必要字段
    required_fields = ['company_name', 'count', 'expires_at']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"缺少必要字段: {field}")
    
    # 检查数量限制
    if 'count' in data:
        count = data['count']
        if not isinstance(count, int) or count < 1 or count > 100:
            errors.append("创建数量必须在1-100之间")
    
    # 检查过期时间
    if 'expires_at' in data:
        try:
            expires_at = data['expires_at']
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expires_at <= get_utc_now():
                errors.append("过期时间必须大于当前时间")
        except Exception:
            errors.append("无效的过期时间格式")
    
    # 检查token长度
    if 'token_length' in data:
        length = data['token_length']
        if not isinstance(length, int) or length < 16 or length > 64:
            errors.append("Token长度必须在16-64之间")
    
    return errors


def export_tokens_to_csv(tokens: List[WhitelistToken]) -> str:
    """将token列表导出为CSV格式"""
    try:
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            'ID', 'Token', '公司名称', '描述', '最大使用次数', '已使用次数',
            '过期时间', '是否激活', '自动审批', '创建时间', '创建者'
        ])
        
        # 写入数据
        for token in tokens:
            writer.writerow([
                token.id,
                token.token,
                token.company_name,
                token.description or '',
                token.max_uses,
                token.used_count,
                token.expires_at.isoformat(),
                '是' if token.is_active else '否',
                '是' if token.auto_approve else '否',
                token.created_at.isoformat(),
                token.created_by or ''
            ])
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"导出token到CSV失败: {e}")
        return ""


def import_tokens_from_csv(csv_content: str, db: Session, created_by: str) -> Dict[str, Any]:
    """从CSV导入token"""
    try:
        import csv
        import io
        
        success_count = 0
        failed_count = 0
        errors = []
        
        # 解析CSV
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        for row_num, row in enumerate(reader, 2):  # 从第2行开始（跳过表头）
            try:
                # 验证必要字段
                if not row.get('公司名称') or not row.get('过期时间'):
                    errors.append(f"第{row_num}行: 缺少必要字段")
                    failed_count += 1
                    continue
                
                # 解析过期时间
                try:
                    expires_at = datetime.fromisoformat(row['过期时间'].replace('Z', '+00:00'))
                except Exception:
                    errors.append(f"第{row_num}行: 无效的过期时间格式")
                    failed_count += 1
                    continue
                
                # 检查是否已过期
                if expires_at <= get_utc_now():
                    errors.append(f"第{row_num}行: 过期时间必须大于当前时间")
                    failed_count += 1
                    continue
                
                # 创建token
                token = WhitelistToken(
                    token=generate_secure_token(),
                    company_name=row['公司名称'].strip(),
                    description=row.get('描述', '').strip() or None,
                    max_uses=int(row.get('最大使用次数', 100)),
                    expires_at=expires_at,
                    is_active=row.get('是否激活', '是').strip() == '是',
                    auto_approve=row.get('自动审批', '否').strip() == '是',
                    created_by=created_by
                )
                
                db.add(token)
                success_count += 1
                
            except Exception as e:
                errors.append(f"第{row_num}行: {str(e)}")
                failed_count += 1
        
        if success_count > 0:
            db.commit()
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"从CSV导入token失败: {e}")
        db.rollback()
        return {
            "success_count": 0,
            "failed_count": 0,
            "errors": [f"导入失败: {str(e)}"]
        }
