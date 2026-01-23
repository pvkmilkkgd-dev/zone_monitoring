from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AdministrativeZoneBase(BaseModel):
    """Базовая схема административной зоны."""
    department_name: str = Field(..., description="Название отдела")
    description: Optional[str] = Field(None, description="Описание подразделения")
    district_names: List[str] = Field(..., description="Список административных районов")


class AdministrativeZoneCreate(AdministrativeZoneBase):
    """Схема для создания административной зоны."""
    map_id: int = Field(..., description="ID карты")
    layer_id: Optional[int] = Field(None, description="ID главного слоя")
    sub_layer_id: Optional[int] = Field(None, description="ID вложенного слоя")
    sub_sub_layer_id: Optional[int] = Field(None, description="ID под-вложенного слоя")


class AdministrativeZoneUpdate(BaseModel):
    """Схема для обновления административной зоны."""
    department_name: Optional[str] = Field(None, description="Название отдела")
    description: Optional[str] = Field(None, description="Описание подразделения")
    district_names: Optional[List[str]] = Field(None, description="Список административных районов")
    layer_id: Optional[int] = Field(None, description="ID главного слоя")
    sub_layer_id: Optional[int] = Field(None, description="ID вложенного слоя")
    sub_sub_layer_id: Optional[int] = Field(None, description="ID под-вложенного слоя")


class AdministrativeZone(AdministrativeZoneBase):
    """Схема административной зоны для ответа."""
    id: int
    map_id: int
    description: Optional[str] = None
    layer_id: Optional[int] = None
    sub_layer_id: Optional[int] = None
    sub_sub_layer_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
