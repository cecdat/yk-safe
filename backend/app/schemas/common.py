from pydantic import BaseModel
from typing import Optional, Any

class ResponseModel(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: Optional[str] = None
