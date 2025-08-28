from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import BlacklistIP
from app.schemas.firewall import BlacklistIPCreate, BlacklistIPResponse
from app.schemas.common import ResponseModel
from app.utils.nftables_generator import NftablesGenerator

router = APIRouter()

@router.get("/", response_model=ResponseModel)
def get_blacklist_ips(db: Session = Depends(get_db)):
    """获取所有黑名单IP"""
    blacklist_ips = db.query(BlacklistIP).filter(BlacklistIP.is_active == True).all()
    
    return ResponseModel(
        code=0,
        message="获取黑名单成功",
        data=[{
            "id": ip.id,
            "ip_address": ip.ip_address,
            "description": ip.description,
            "created_at": ip.created_at,
            "is_active": ip.is_active
        } for ip in blacklist_ips]
    )

@router.post("/", response_model=ResponseModel)
def add_blacklist_ip(blacklist_ip: BlacklistIPCreate, db: Session = Depends(get_db)):
    """添加黑名单IP - 实时生效并踢下线"""
    # 检查IP是否已存在
    existing_ip = db.query(BlacklistIP).filter(
        BlacklistIP.ip_address == blacklist_ip.ip_address,
        BlacklistIP.is_active == True
    ).first()
    
    if existing_ip:
        raise HTTPException(status_code=400, detail="IP地址已在黑名单中")
    
    # 使用实时方法添加IP到黑名单
    generator = NftablesGenerator(db)
    success = generator.add_ip_to_blacklist_realtime(
        ip_address=blacklist_ip.ip_address,
        description=blacklist_ip.description
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="添加黑名单IP失败")
    
    # 获取刚添加的IP信息
    added_ip = db.query(BlacklistIP).filter(
        BlacklistIP.ip_address == blacklist_ip.ip_address,
        BlacklistIP.is_active == True
    ).first()
    
    return ResponseModel(
        code=0,
        message="添加黑名单IP成功，已立即生效并踢下线",
        data={
            "id": added_ip.id,
            "ip_address": added_ip.ip_address,
            "description": added_ip.description
        }
    )

@router.delete("/{ip_id}", response_model=ResponseModel)
def remove_blacklist_ip(ip_id: int, db: Session = Depends(get_db)):
    """删除黑名单IP - 实时生效"""
    blacklist_ip = db.query(BlacklistIP).filter(BlacklistIP.id == ip_id).first()
    if not blacklist_ip:
        raise HTTPException(status_code=404, detail="黑名单IP不存在")
    
    # 使用实时方法从黑名单移除IP
    generator = NftablesGenerator(db)
    success = generator.remove_ip_from_blacklist_realtime(blacklist_ip.ip_address)
    
    if not success:
        raise HTTPException(status_code=500, detail="删除黑名单IP失败")
    
    return ResponseModel(
        code=0,
        message="删除黑名单IP成功，已立即生效",
        data={"ip_address": blacklist_ip.ip_address}
    )

@router.get("/count", response_model=ResponseModel)
def get_blacklist_count(db: Session = Depends(get_db)):
    """获取黑名单IP数量"""
    count = db.query(BlacklistIP).filter(BlacklistIP.is_active == True).count()
    
    return ResponseModel(
        code=0,
        message="获取黑名单数量成功",
        data={"count": count}
    )

@router.get("/connections/{ip_address}", response_model=ResponseModel)
def get_ip_connections(ip_address: str, db: Session = Depends(get_db)):
    """获取指定IP的活跃连接信息"""
    generator = NftablesGenerator(db)
    connections = generator.get_active_connections(ip_address)
    
    return ResponseModel(
        code=0,
        message="获取连接信息成功",
        data={
            "ip_address": ip_address,
            "connections": connections,
            "count": len(connections)
        }
    )

@router.get("/connections", response_model=ResponseModel)
def get_all_connections(db: Session = Depends(get_db)):
    """获取所有活跃连接信息"""
    generator = NftablesGenerator(db)
    connections = generator.get_active_connections()
    
    return ResponseModel(
        code=0,
        message="获取所有连接信息成功",
        data={
            "connections": connections,
            "count": len(connections)
        }
    )

@router.post("/terminate/{ip_address}", response_model=ResponseModel)
def terminate_ip_connections(ip_address: str, db: Session = Depends(get_db)):
    """终止指定IP的所有活跃连接"""
    generator = NftablesGenerator(db)
    success = generator._terminate_active_connections(ip_address)
    
    if success:
        return ResponseModel(
            code=0,
            message=f"已成功终止IP {ip_address} 的所有活跃连接",
            data={"ip_address": ip_address, "terminated": True}
        )
    else:
        raise HTTPException(status_code=500, detail=f"终止IP {ip_address} 的连接失败")
