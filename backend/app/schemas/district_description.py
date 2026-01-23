from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DistrictDescriptionBase(BaseModel):
    """Базовая схема описания района."""
    district_name: str = Field(..., description="Название района")
    description: Optional[str] = Field(None, description="Описание района")


class DistrictDescriptionCreate(DistrictDescriptionBase):
    """Схема для создания описания района."""
    pass


class DistrictDescriptionUpdate(BaseModel):
    """Схема для обновления описания района."""
    description: Optional[str] = Field(None, description="Описание района")


class DistrictDescription(DistrictDescriptionBase):
    """Схема описания района для ответа."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
