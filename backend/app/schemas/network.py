from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CaptureCreate(BaseModel):
    protocol: Optional[str] = None
    interface: str
    source_ip: Optional[str] = None
    target_ip: Optional[str] = None
    duration: int = 60

class CaptureResponse(BaseModel):
    id: int
    task_id: str
    protocol: str
    interface: str
    source_ip: Optional[str]
    target_ip: Optional[str]
    duration: int
    status: str
    filename: Optional[str]
    file_size: Optional[int]
    created_at: datetime

class TaskStatus(BaseModel):
    status: str
    progress: int
    output: str
    error: Optional[str] = None

class InterfaceInfo(BaseModel):
    name: str
    ip: Optional[str] = None

class PingRequest(BaseModel):
    target: str

class TracerouteRequest(BaseModel):
    target: str
