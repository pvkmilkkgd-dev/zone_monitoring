from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class EventImageOut(BaseModel):
    """Схема изображения события для ответа."""
    id: int
    name: str
    file_path: str
    created_at: datetime

    class Config:
        from_attributes = True


class EventDocumentOut(BaseModel):
    """Схема документа события для ответа."""
    id: int
    name: str
    file_path: str
    created_at: datetime

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    """Схема для создания события."""
    map_id: int = Field(..., description="ID карты")
    district_name: str = Field(..., description="Название района")
    title: str = Field(..., min_length=1, max_length=255, description="Название события")
    description: Optional[str] = Field(None, description="Описание события")
    importance: int = Field(5, ge=1, le=10, description="Коэффициент важности от 1 до 10")
    layer_id: Optional[int] = Field(None, description="ID главного слоя")
    sub_layer_id: Optional[int] = Field(None, description="ID вложенного слоя")
    sub_sub_layer_id: Optional[int] = Field(None, description="ID под-вложенного слоя")


class EventUpdate(BaseModel):
    """Схема для обновления события."""
    district_name: Optional[str] = Field(None, description="Название района")
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Название события")
    description: Optional[str] = Field(None, description="Описание события")
    importance: Optional[int] = Field(None, ge=1, le=10, description="Коэффициент важности")
    status: Optional[str] = Field(None, description="Статус события")
    layer_id: Optional[int] = Field(None, description="ID главного слоя")
    sub_layer_id: Optional[int] = Field(None, description="ID вложенного слоя")
    sub_sub_layer_id: Optional[int] = Field(None, description="ID под-вложенного слоя")


class EventOut(BaseModel):
    """Схема события для ответа."""
    id: int
    map_id: int
    administrative_zone_id: Optional[int] = None
    department_name: Optional[str] = None
    district_name: Optional[str] = None
    status: str
    title: str
    description: Optional[str] = None
    importance: int
    layer_id: Optional[int] = None
    sub_layer_id: Optional[int] = None
    sub_sub_layer_id: Optional[int] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    images: List[EventImageOut] = []
    documents: List[EventDocumentOut] = []

    class Config:
        from_attributes = True


class EventListOut(BaseModel):
    """Схема события для списка (без файлов)."""
    id: int
    map_id: int
    administrative_zone_id: Optional[int] = None
    department_name: Optional[str] = None
    district_name: Optional[str] = None
    status: str
    title: str
    description: Optional[str] = None
    importance: int
    layer_id: Optional[int] = None
    sub_layer_id: Optional[int] = None
    sub_sub_layer_id: Optional[int] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    images_count: int = 0
    documents_count: int = 0

    class Config:
        from_attributes = True
