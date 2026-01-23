from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel


class AuditLogOut(BaseModel):
    """Схема для вывода записи журнала."""
    id: int
    action: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    description: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogListOut(BaseModel):
    """Схема для списка записей журнала с пагинацией."""
    items: list[AuditLogOut]
    total: int
    page: int
    per_page: int
    pages: int
