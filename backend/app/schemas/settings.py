from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class PushConfigCreate(BaseModel):
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_types: Optional[List[str]] = None
    bark_enabled: bool = False
    bark_url: Optional[str] = None
    bark_types: Optional[List[str]] = None

class BackupResponse(BaseModel):
    id: int
    backup_id: str
    filename: str
    file_size: Optional[int]
    status: str
    created_at: datetime
