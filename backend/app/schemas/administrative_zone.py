from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AdministrativeZoneBase(BaseModel):
    """Базовая схема административной зоны."""
    department_name: str = Field(..., description="Название отдела")
    district_names: List[str] = Field(..., description="Список административных районов")


class AdministrativeZoneCreate(AdministrativeZoneBase):
    """Схема для создания административной зоны."""
    map_id: int = Field(..., description="ID карты")


class AdministrativeZoneUpdate(BaseModel):
    """Схема для обновления административной зоны."""
    department_name: Optional[str] = Field(None, description="Название отдела")
    district_names: Optional[List[str]] = Field(None, description="Список административных районов")


class AdministrativeZone(AdministrativeZoneBase):
    """Схема административной зоны для ответа."""
    id: int
    map_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
