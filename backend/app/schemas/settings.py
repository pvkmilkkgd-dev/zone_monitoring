from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class SystemSettingsResponse(BaseModel):
    id: int
    department_name: Optional[str] = None
    region_ids: List[UUID] = []

    # для совместимости со старым полем
    region: Optional[str] = None

    model_config = {"from_attributes": True}


class SystemSettingsUpdate(BaseModel):
    department_name: Optional[str] = None
    region_ids: Optional[List[UUID]] = None

    # старое поле, если фронт еще шлёт строку
    region: Optional[str] = None
