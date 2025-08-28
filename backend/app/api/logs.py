from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import SystemLog, FirewallLog
from app.schemas.common import ResponseModel

router = APIRouter()

@router.get("/system", response_model=ResponseModel)
def get_system_logs(
    db: Session = Depends(get_db),
    level: Optional[str] = Query(None, description="日志级别: info, warning, error"),
    source: Optional[str] = Query(None, description="日志来源: firewall, blacklist, system"),
    limit: int = Query(100, description="返回日志数量限制"),
    days: int = Query(7, description="查询最近几天的日志")
):
    """获取系统日志"""
    query = db.query(SystemLog)
    
    # 按级别过滤
    if level:
        query = query.filter(SystemLog.level == level)
    
    # 按来源过滤
    if source:
        query = query.filter(SystemLog.source == source)
    
    # 按时间过滤
    if days > 0:
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(SystemLog.created_at >= start_date)
    
    # 按时间倒序排列并限制数量
    logs = query.order_by(SystemLog.created_at.desc()).limit(limit).all()
    
    return ResponseModel(
        code=0,
        message="获取系统日志成功",
        data=[{
            "id": log.id,
            "level": log.level,
            "message": log.message,
            "source": log.source,
            "created_at": log.created_at
        } for log in logs]
    )

@router.get("/firewall", response_model=ResponseModel)
def get_firewall_logs(
    db: Session = Depends(get_db),
    action: Optional[str] = Query(None, description="动作: drop, accept, reject"),
    protocol: Optional[str] = Query(None, description="协议: tcp, udp, icmp, all"),
    threat_level: Optional[str] = Query(None, description="威胁等级: low, medium, high, critical"),
    source_ip: Optional[str] = Query(None, description="源IP地址"),
    destination_ip: Optional[str] = Query(None, description="目标IP地址"),
    rule_name: Optional[str] = Query(None, description="规则名称"),
    country: Optional[str] = Query(None, description="源IP国家"),
    limit: int = Query(100, description="返回日志数量限制"),
    days: int = Query(1, description="查询最近几天的日志"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(50, description="每页数量")
):
    """获取防火墙日志"""
    query = db.query(FirewallLog)
    
    # 按动作过滤
    if action:
        query = query.filter(FirewallLog.action == action)
    
    # 按协议过滤
    if protocol:
        query = query.filter(FirewallLog.protocol == protocol)
    
    # 按威胁等级过滤
    if threat_level:
        query = query.filter(FirewallLog.threat_level == threat_level)
    
    # 按源IP过滤
    if source_ip:
        query = query.filter(FirewallLog.source_ip.contains(source_ip))
    
    # 按目标IP过滤
    if destination_ip:
        query = query.filter(FirewallLog.destination_ip.contains(destination_ip))
    
    # 按规则名称过滤
    if rule_name:
        query = query.filter(FirewallLog.rule_name.contains(rule_name))
    
    # 按国家过滤
    if country:
        query = query.filter(FirewallLog.country.contains(country))
    
    # 按时间过滤
    if days > 0:
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(FirewallLog.timestamp >= start_date)
    
    # 计算总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    logs = query.order_by(FirewallLog.timestamp.desc()).offset(offset).limit(page_size).all()
    
    return ResponseModel(
        code=0,
        message="获取防火墙日志成功",
        data={
            "logs": [{
                "id": log.id,
                "source_ip": log.source_ip,
                "destination_ip": log.destination_ip,
                "protocol": log.protocol,
                "source_port": log.source_port,
                "destination_port": log.destination_port,
                "action": log.action,
                "rule_id": log.rule_id,
                "rule_name": log.rule_name,
                "interface": log.interface,
                "packet_size": log.packet_size,
                "tcp_flags": log.tcp_flags,
                "country": log.country,
                "city": log.city,
                "isp": log.isp,
                "threat_level": log.threat_level,
                "description": log.description,
                "timestamp": log.timestamp
            } for log in logs],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size
            }
        }
    )

@router.post("/system", response_model=ResponseModel)
def add_system_log(
    level: str,
    message: str,
    source: str = "system",
    db: Session = Depends(get_db)
):
    """添加系统日志"""
    log = SystemLog(
        level=level,
        message=message,
        source=source
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return ResponseModel(
        code=0,
        message="添加系统日志成功",
        data={"id": log.id}
    )

@router.get("/stats", response_model=ResponseModel)
def get_log_stats(db: Session = Depends(get_db)):
    """获取日志统计信息"""
    # 系统日志统计
    total_system_logs = db.query(SystemLog).count()
    error_logs = db.query(SystemLog).filter(SystemLog.level == "error").count()
    warning_logs = db.query(SystemLog).filter(SystemLog.level == "warning").count()
    
    # 防火墙日志统计
    total_firewall_logs = db.query(FirewallLog).count()
    drop_logs = db.query(FirewallLog).filter(FirewallLog.action == "drop").count()
    accept_logs = db.query(FirewallLog).filter(FirewallLog.action == "accept").count()
    reject_logs = db.query(FirewallLog).filter(FirewallLog.action == "reject").count()
    
    # 最近24小时的日志数量
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_system_logs = db.query(SystemLog).filter(SystemLog.created_at >= yesterday).count()
    recent_firewall_logs = db.query(FirewallLog).filter(FirewallLog.timestamp >= yesterday).count()
    
    # 威胁等级统计
    threat_stats = db.query(
        FirewallLog.threat_level,
        db.func.count(FirewallLog.id).label('count')
    ).filter(
        FirewallLog.timestamp >= yesterday
    ).group_by(FirewallLog.threat_level).all()
    
    # 协议统计
    protocol_stats = db.query(
        FirewallLog.protocol,
        db.func.count(FirewallLog.id).label('count')
    ).filter(
        FirewallLog.timestamp >= yesterday
    ).group_by(FirewallLog.protocol).all()
    
    # 国家统计（前5个）
    country_stats = db.query(
        FirewallLog.country,
        db.func.count(FirewallLog.id).label('count')
    ).filter(
        FirewallLog.timestamp >= yesterday,
        FirewallLog.country.isnot(None)
    ).group_by(FirewallLog.country).order_by(
        db.func.count(FirewallLog.id).desc()
    ).limit(5).all()
    
    return ResponseModel(
        code=0,
        message="获取日志统计成功",
        data={
            "system_logs": {
                "total": total_system_logs,
                "errors": error_logs,
                "warnings": warning_logs,
                "recent_24h": recent_system_logs
            },
            "firewall_logs": {
                "total": total_firewall_logs,
                "drops": drop_logs,
                "accepts": accept_logs,
                "rejects": reject_logs,
                "recent_24h": recent_firewall_logs
            },
            "threat_stats": {stat.threat_level: stat.count for stat in threat_stats},
            "protocol_stats": {stat.protocol: stat.count for stat in protocol_stats},
            "country_stats": [{"country": stat.country, "count": stat.count} for stat in country_stats]
        }
    )

@router.get("/firewall/summary", response_model=ResponseModel)
def get_firewall_log_summary(
    db: Session = Depends(get_db),
    hours: int = Query(24, description="统计最近几小时的日志")
):
    """获取防火墙日志摘要统计"""
    try:
        from app.utils.firewall_logger import FirewallLogger
        logger = FirewallLogger(db)
        summary = logger.get_log_summary(hours)
        
        return ResponseModel(
            code=0,
            message="获取防火墙日志摘要成功",
            data=summary
        )
    except Exception as e:
        return ResponseModel(
            code=5000,
            message=f"获取防火墙日志摘要失败: {str(e)}"
        )

@router.post("/firewall/cleanup", response_model=ResponseModel)
def cleanup_firewall_logs(
    days: int = Query(30, description="清理几天前的日志"),
    db: Session = Depends(get_db)
):
    """清理旧防火墙日志"""
    try:
        from app.utils.firewall_logger import FirewallLogger
        logger = FirewallLogger(db)
        deleted_count = logger.cleanup_old_logs(days)
        
        return ResponseModel(
            code=0,
            message=f"清理防火墙日志成功，删除了 {deleted_count} 条记录",
            data={"deleted_count": deleted_count}
        )
    except Exception as e:
        return ResponseModel(
            code=5000,
            message=f"清理防火墙日志失败: {str(e)}"
        )

@router.get("/firewall/export", response_model=ResponseModel)
def export_firewall_logs(
    db: Session = Depends(get_db),
    days: int = Query(7, description="导出最近几天的日志"),
    format: str = Query("csv", description="导出格式: csv, json")
):
    """导出防火墙日志"""
    try:
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = db.query(FirewallLog).filter(
            FirewallLog.timestamp >= start_date
        ).order_by(FirewallLog.timestamp.desc()).all()
        
        if format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow([
                "时间", "源IP", "目标IP", "协议", "源端口", "目标端口", 
                "动作", "规则名称", "威胁等级", "国家", "城市", "描述"
            ])
            
            # 写入数据
            for log in logs:
                writer.writerow([
                    log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    log.source_ip,
                    log.destination_ip,
                    log.protocol,
                    log.source_port or "",
                    log.destination_port or "",
                    log.action,
                    log.rule_name or "",
                    log.threat_level,
                    log.country or "",
                    log.city or "",
                    log.description or ""
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            return ResponseModel(
                code=0,
                message="导出CSV成功",
                data={
                    "content": csv_content,
                    "filename": f"firewall_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
        
        else:  # JSON格式
            log_data = [{
                "timestamp": log.timestamp.isoformat(),
                "source_ip": log.source_ip,
                "destination_ip": log.destination_ip,
                "protocol": log.protocol,
                "source_port": log.source_port,
                "destination_port": log.destination_port,
                "action": log.action,
                "rule_name": log.rule_name,
                "threat_level": log.threat_level,
                "country": log.country,
                "city": log.city,
                "description": log.description
            } for log in logs]
            
            return ResponseModel(
                code=0,
                message="导出JSON成功",
                data={
                    "content": log_data,
                    "filename": f"firewall_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                }
            )
            
    except Exception as e:
        return ResponseModel(
            code=5000,
            message=f"导出防火墙日志失败: {str(e)}"
        )
