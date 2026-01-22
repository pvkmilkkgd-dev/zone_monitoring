from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.models.layer import Layer, SubLayer, SubSubLayer
from app.schemas.layer import (
    LayerOut,
    LayerCreate,
    LayerUpdate,
    SubLayerOut,
    SubLayerCreate,
    SubLayerUpdate,
    SubSubLayerOut,
    SubSubLayerCreate,
    SubSubLayerUpdate,
)


class ReorderItem(BaseModel):
    id: int
    order: int


class ReorderRequest(BaseModel):
    items: List[ReorderItem]


router = APIRouter(prefix="/layers", tags=["layers"])


@router.get("/", response_model=List[LayerOut])
def list_layers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить список всех слоев с вложенными."""
    layers = (
        db.query(Layer)
        .options(
            joinedload(Layer.sub_layers).joinedload(SubLayer.sub_sub_layers)
        )
        .order_by(Layer.order, Layer.id)
        .all()
    )
    return layers


@router.get("/{layer_id}", response_model=LayerOut)
def get_layer(
    layer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить слой по ID."""
    layer = (
        db.query(Layer)
        .options(
            joinedload(Layer.sub_layers).joinedload(SubLayer.sub_sub_layers)
        )
        .filter(Layer.id == layer_id)
        .first()
    )
    if not layer:
        raise HTTPException(status_code=404, detail="Слой не найден")
    return layer


@router.post("/", response_model=LayerOut)
def create_layer(
    data: LayerCreate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Создать новый главный слой."""
    # Проверка на дубликат названия
    existing = db.query(Layer).filter(
        func.lower(Layer.name) == data.name.lower().strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Слой с таким названием уже существует"
        )
    
    # Получить максимальный order для новой позиции
    max_order = db.query(func.max(Layer.order)).scalar() or 0
    
    layer = Layer(
        name=data.name.strip(),
        map_id=data.map_id,
        order=max_order + 1,
    )
    db.add(layer)
    db.commit()
    db.refresh(layer)
    
    return layer


@router.patch("/{layer_id}", response_model=LayerOut)
def update_layer(
    layer_id: int,
    data: LayerUpdate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Обновить слой."""
    layer = db.query(Layer).filter(Layer.id == layer_id).first()
    if not layer:
        raise HTTPException(status_code=404, detail="Слой не найден")
    
    if data.name is not None:
        # Проверка на дубликат названия (исключая текущий слой)
        existing = db.query(Layer).filter(
            func.lower(Layer.name) == data.name.lower().strip(),
            Layer.id != layer_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Слой с таким названием уже существует"
            )
        layer.name = data.name.strip()
    
    if data.is_visible is not None:
        layer.is_visible = data.is_visible
    
    if data.order is not None:
        layer.order = data.order
    
    db.commit()
    db.refresh(layer)
    
    # Загружаем sub_layers для ответа
    layer = (
        db.query(Layer)
        .options(
            joinedload(Layer.sub_layers).joinedload(SubLayer.sub_sub_layers)
        )
        .filter(Layer.id == layer_id)
        .first()
    )
    
    return layer


@router.delete("/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_layer(
    layer_id: int,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Удалить слой (вместе с вложенными)."""
    layer = db.query(Layer).filter(Layer.id == layer_id).first()
    if not layer:
        raise HTTPException(status_code=404, detail="Слой не найден")
    
    db.delete(layer)
    db.commit()
    return None


@router.post("/reorder", response_model=List[LayerOut])
def reorder_layers(
    data: ReorderRequest,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Изменить порядок главных слоёв."""
    for item in data.items:
        layer = db.query(Layer).filter(Layer.id == item.id).first()
        if layer:
            layer.order = item.order
    
    db.commit()
    
    # Возвращаем обновленный список
    layers = (
        db.query(Layer)
        .options(
            joinedload(Layer.sub_layers).joinedload(SubLayer.sub_sub_layers)
        )
        .order_by(Layer.order, Layer.id)
        .all()
    )
    return layers


# === SubLayer endpoints ===

@router.post("/sublayers", response_model=SubLayerOut)
def create_sublayer(
    data: SubLayerCreate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Создать новый вложенный слой."""
    # Проверка существования родительского слоя
    parent = db.query(Layer).filter(Layer.id == data.parent_layer_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Родительский слой не найден")
    
    # Проверка на дубликат названия в рамках родительского слоя
    existing = db.query(SubLayer).filter(
        SubLayer.parent_layer_id == data.parent_layer_id,
        func.lower(SubLayer.name) == data.name.lower().strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вложенный слой с таким названием уже существует"
        )
    
    # Получить максимальный order для новой позиции в рамках родительского слоя
    max_order = db.query(func.max(SubLayer.order)).filter(
        SubLayer.parent_layer_id == data.parent_layer_id
    ).scalar() or 0
    
    sublayer = SubLayer(
        name=data.name.strip(),
        parent_layer_id=data.parent_layer_id,
        order=max_order + 1,
    )
    db.add(sublayer)
    db.commit()
    db.refresh(sublayer)
    
    return sublayer


@router.patch("/sublayers/{sublayer_id}", response_model=SubLayerOut)
def update_sublayer(
    sublayer_id: int,
    data: SubLayerUpdate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Обновить вложенный слой."""
    sublayer = db.query(SubLayer).filter(SubLayer.id == sublayer_id).first()
    if not sublayer:
        raise HTTPException(status_code=404, detail="Вложенный слой не найден")
    
    if data.name is not None:
        # Проверка на дубликат названия в рамках родительского слоя
        existing = db.query(SubLayer).filter(
            SubLayer.parent_layer_id == sublayer.parent_layer_id,
            func.lower(SubLayer.name) == data.name.lower().strip(),
            SubLayer.id != sublayer_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вложенный слой с таким названием уже существует"
            )
        sublayer.name = data.name.strip()
    
    if data.is_visible is not None:
        sublayer.is_visible = data.is_visible
    
    if data.order is not None:
        sublayer.order = data.order
    
    db.commit()
    db.refresh(sublayer)
    
    return sublayer


@router.delete("/sublayers/{sublayer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sublayer(
    sublayer_id: int,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Удалить вложенный слой."""
    sublayer = db.query(SubLayer).filter(SubLayer.id == sublayer_id).first()
    if not sublayer:
        raise HTTPException(status_code=404, detail="Вложенный слой не найден")
    
    db.delete(sublayer)
    db.commit()
    return None


@router.post("/sublayers/reorder")
def reorder_sublayers(
    data: ReorderRequest,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Изменить порядок вложенных слоёв."""
    for item in data.items:
        sublayer = db.query(SubLayer).filter(SubLayer.id == item.id).first()
        if sublayer:
            sublayer.order = item.order
    
    db.commit()
    return {"status": "ok"}


# === SubSubLayer endpoints ===

@router.post("/subsublayers", response_model=SubSubLayerOut)
def create_subsublayer(
    data: SubSubLayerCreate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Создать новый под-вложенный слой (третий уровень)."""
    # Проверка существования родительского вложенного слоя
    parent = db.query(SubLayer).filter(SubLayer.id == data.parent_sub_layer_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Родительский вложенный слой не найден")
    
    # Проверка на дубликат названия в рамках родительского слоя
    existing = db.query(SubSubLayer).filter(
        SubSubLayer.parent_sub_layer_id == data.parent_sub_layer_id,
        func.lower(SubSubLayer.name) == data.name.lower().strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Под-вложенный слой с таким названием уже существует"
        )
    
    # Получить максимальный order для новой позиции
    max_order = db.query(func.max(SubSubLayer.order)).filter(
        SubSubLayer.parent_sub_layer_id == data.parent_sub_layer_id
    ).scalar() or 0
    
    subsublayer = SubSubLayer(
        name=data.name.strip(),
        parent_sub_layer_id=data.parent_sub_layer_id,
        order=max_order + 1,
    )
    db.add(subsublayer)
    db.commit()
    db.refresh(subsublayer)
    
    return subsublayer


@router.patch("/subsublayers/{subsublayer_id}", response_model=SubSubLayerOut)
def update_subsublayer(
    subsublayer_id: int,
    data: SubSubLayerUpdate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Обновить под-вложенный слой."""
    subsublayer = db.query(SubSubLayer).filter(SubSubLayer.id == subsublayer_id).first()
    if not subsublayer:
        raise HTTPException(status_code=404, detail="Под-вложенный слой не найден")
    
    if data.name is not None:
        # Проверка на дубликат названия
        existing = db.query(SubSubLayer).filter(
            SubSubLayer.parent_sub_layer_id == subsublayer.parent_sub_layer_id,
            func.lower(SubSubLayer.name) == data.name.lower().strip(),
            SubSubLayer.id != subsublayer_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Под-вложенный слой с таким названием уже существует"
            )
        subsublayer.name = data.name.strip()
    
    if data.is_visible is not None:
        subsublayer.is_visible = data.is_visible
    
    if data.order is not None:
        subsublayer.order = data.order
    
    db.commit()
    db.refresh(subsublayer)
    
    return subsublayer


@router.delete("/subsublayers/{subsublayer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subsublayer(
    subsublayer_id: int,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Удалить под-вложенный слой."""
    subsublayer = db.query(SubSubLayer).filter(SubSubLayer.id == subsublayer_id).first()
    if not subsublayer:
        raise HTTPException(status_code=404, detail="Под-вложенный слой не найден")
    
    db.delete(subsublayer)
    db.commit()
    return None


@router.post("/subsublayers/reorder")
def reorder_subsublayers(
    data: ReorderRequest,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Изменить порядок под-вложенных слоёв."""
    for item in data.items:
        subsublayer = db.query(SubSubLayer).filter(SubSubLayer.id == item.id).first()
        if subsublayer:
            subsublayer.order = item.order
    
    db.commit()
    return {"status": "ok"}
