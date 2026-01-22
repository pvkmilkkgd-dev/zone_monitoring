from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# === SubSubLayer (третий уровень) ===

class SubSubLayerBase(BaseModel):
    name: str


class SubSubLayerCreate(SubSubLayerBase):
    parent_sub_layer_id: int


class SubSubLayerUpdate(BaseModel):
    name: Optional[str] = None
    is_visible: Optional[bool] = None
    order: Optional[int] = None


class SubSubLayerOut(SubSubLayerBase):
    id: int
    parent_sub_layer_id: int
    is_visible: bool
    order: int

    class Config:
        from_attributes = True


# === SubLayer (второй уровень) ===

class SubLayerBase(BaseModel):
    name: str


class SubLayerCreate(SubLayerBase):
    parent_layer_id: int


class SubLayerUpdate(BaseModel):
    name: Optional[str] = None
    is_visible: Optional[bool] = None
    order: Optional[int] = None


class SubLayerOut(SubLayerBase):
    id: int
    parent_layer_id: int
    is_visible: bool
    order: int
    sub_sub_layers: List[SubSubLayerOut] = []

    class Config:
        from_attributes = True


# === Layer (первый уровень) ===

class LayerBase(BaseModel):
    name: str
    map_id: int


class LayerCreate(LayerBase):
    pass


class LayerUpdate(BaseModel):
    name: Optional[str] = None
    is_visible: Optional[bool] = None
    order: Optional[int] = None


class LayerOut(LayerBase):
    id: int
    is_visible: bool
    order: int
    sub_layers: List[SubLayerOut] = []

    class Config:
        from_attributes = True
