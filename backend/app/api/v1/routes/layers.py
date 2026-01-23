from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.models.layer import Layer, SubLayer, SubSubLayer
from app.services.audit_service import AuditService
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
    """Получить список всех слоев с вложенными (без удалённых)."""
    layers = (
        db.query(Layer)
        .filter(Layer.is_deleted == False)
        .options(
            joinedload(Layer.sub_layers.and_(SubLayer.is_deleted == False))
            .joinedload(SubLayer.sub_sub_layers.and_(SubSubLayer.is_deleted == False))
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
        .filter(Layer.id == layer_id, Layer.is_deleted == False)
        .options(
            joinedload(Layer.sub_layers.and_(SubLayer.is_deleted == False))
            .joinedload(SubLayer.sub_sub_layers.and_(SubSubLayer.is_deleted == False))
        )
        .first()
    )
    if not layer:
        raise HTTPException(status_code=404, detail="Слой не найден")
    return layer


@router.post("/", response_model=LayerOut)
def create_layer(
    request: Request,
    data: LayerCreate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Создать новый главный слой."""
    # Проверка на дубликат названия (среди не удалённых)
    existing = db.query(Layer).filter(
        func.lower(Layer.name) == data.name.lower().strip(),
        Layer.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Слой с таким названием уже существует"
        )
    
    # Получить максимальный order для новой позиции (среди не удалённых)
    max_order = db.query(func.max(Layer.order)).filter(Layer.is_deleted == False).scalar() or 0
    
    layer = Layer(
        name=data.name.strip(),
        map_id=data.map_id,
        order=max_order + 1,
    )
    db.add(layer)
    db.commit()
    db.refresh(layer)
    
    # Логируем
    AuditService(db).log(
        action="CREATE",
        user=current_user,
        entity_type="layer",
        entity_id=layer.id,
        entity_name=layer.name,
        description=f"Создан слой '{layer.name}'",
        request=request,
    )
    
    return layer


@router.patch("/{layer_id}", response_model=LayerOut)
def update_layer(
    request: Request,
    layer_id: int,
    data: LayerUpdate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Обновить слой."""
    layer = db.query(Layer).filter(Layer.id == layer_id, Layer.is_deleted == False).first()
    if not layer:
        raise HTTPException(status_code=404, detail="Слой не найден")
    
    old_name = layer.name
    changes = {}
    
    if data.name is not None:
        # Проверка на дубликат названия (исключая текущий слой и удалённые)
        existing = db.query(Layer).filter(
            func.lower(Layer.name) == data.name.lower().strip(),
            Layer.id != layer_id,
            Layer.is_deleted == False
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Слой с таким названием уже существует"
            )
        if layer.name != data.name.strip():
            changes["name"] = {"old": layer.name, "new": data.name.strip()}
        layer.name = data.name.strip()
    
    if data.is_visible is not None:
        if layer.is_visible != data.is_visible:
            changes["is_visible"] = {"old": layer.is_visible, "new": data.is_visible}
        layer.is_visible = data.is_visible
    
    if data.order is not None:
        if layer.order != data.order:
            changes["order"] = {"old": layer.order, "new": data.order}
        layer.order = data.order
    
    db.commit()
    db.refresh(layer)
    
    # Логируем
    if changes:
        AuditService(db).log(
            action="UPDATE",
            user=current_user,
            entity_type="layer",
            entity_id=layer.id,
            entity_name=layer.name,
            description=f"Обновлён слой '{old_name}'",
            details={"changes": changes},
            request=request,
        )
    
    # Загружаем sub_layers для ответа (без удалённых)
    layer = (
        db.query(Layer)
        .filter(Layer.id == layer_id)
        .options(
            joinedload(Layer.sub_layers.and_(SubLayer.is_deleted == False))
            .joinedload(SubLayer.sub_sub_layers.and_(SubSubLayer.is_deleted == False))
        )
        .first()
    )
    
    return layer


@router.delete("/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_layer(
    request: Request,
    layer_id: int,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Мягкое удаление слоя (вместе с вложенными)."""
    layer = db.query(Layer).filter(Layer.id == layer_id, Layer.is_deleted == False).first()
    if not layer:
        raise HTTPException(status_code=404, detail="Слой не найден")
    
    layer_name = layer.name
    
    # Мягкое удаление - помечаем слой и все вложенные как удалённые
    layer.is_deleted = True
    for sub in layer.sub_layers:
        sub.is_deleted = True
        for subsub in sub.sub_sub_layers:
            subsub.is_deleted = True
    
    db.commit()
    
    # Логируем
    AuditService(db).log(
        action="DELETE",
        user=current_user,
        entity_type="layer",
        entity_id=layer_id,
        entity_name=layer_name,
        description=f"Удалён слой '{layer_name}'",
        request=request,
    )
    
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
    request: Request,
    data: SubLayerCreate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Создать новый вложенный слой."""
    # Проверка существования родительского слоя (не удалённого)
    parent = db.query(Layer).filter(Layer.id == data.parent_layer_id, Layer.is_deleted == False).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Родительский слой не найден")
    
    # Проверка на дубликат названия в рамках родительского слоя (среди не удалённых)
    existing = db.query(SubLayer).filter(
        SubLayer.parent_layer_id == data.parent_layer_id,
        func.lower(SubLayer.name) == data.name.lower().strip(),
        SubLayer.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вложенный слой с таким названием уже существует"
        )
    
    # Получить максимальный order для новой позиции (среди не удалённых)
    max_order = db.query(func.max(SubLayer.order)).filter(
        SubLayer.parent_layer_id == data.parent_layer_id,
        SubLayer.is_deleted == False
    ).scalar() or 0
    
    sublayer = SubLayer(
        name=data.name.strip(),
        parent_layer_id=data.parent_layer_id,
        order=max_order + 1,
    )
    db.add(sublayer)
    db.commit()
    db.refresh(sublayer)
    
    # Логируем
    AuditService(db).log(
        action="CREATE",
        user=current_user,
        entity_type="sub_layer",
        entity_id=sublayer.id,
        entity_name=sublayer.name,
        description=f"Создан вложенный слой '{sublayer.name}' в слое '{parent.name}'",
        request=request,
    )
    
    return sublayer


@router.patch("/sublayers/{sublayer_id}", response_model=SubLayerOut)
def update_sublayer(
    request: Request,
    sublayer_id: int,
    data: SubLayerUpdate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Обновить вложенный слой."""
    sublayer = db.query(SubLayer).filter(SubLayer.id == sublayer_id, SubLayer.is_deleted == False).first()
    if not sublayer:
        raise HTTPException(status_code=404, detail="Вложенный слой не найден")
    
    old_name = sublayer.name
    changes = {}
    
    if data.name is not None:
        # Проверка на дубликат названия (среди не удалённых)
        existing = db.query(SubLayer).filter(
            SubLayer.parent_layer_id == sublayer.parent_layer_id,
            func.lower(SubLayer.name) == data.name.lower().strip(),
            SubLayer.id != sublayer_id,
            SubLayer.is_deleted == False
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вложенный слой с таким названием уже существует"
            )
        if sublayer.name != data.name.strip():
            changes["name"] = {"old": sublayer.name, "new": data.name.strip()}
        sublayer.name = data.name.strip()
    
    if data.is_visible is not None:
        if sublayer.is_visible != data.is_visible:
            changes["is_visible"] = {"old": sublayer.is_visible, "new": data.is_visible}
        sublayer.is_visible = data.is_visible
    
    if data.order is not None:
        if sublayer.order != data.order:
            changes["order"] = {"old": sublayer.order, "new": data.order}
        sublayer.order = data.order
    
    db.commit()
    db.refresh(sublayer)
    
    # Логируем
    if changes:
        AuditService(db).log(
            action="UPDATE",
            user=current_user,
            entity_type="sub_layer",
            entity_id=sublayer.id,
            entity_name=sublayer.name,
            description=f"Обновлён вложенный слой '{old_name}'",
            details={"changes": changes},
            request=request,
        )
    
    return sublayer


@router.delete("/sublayers/{sublayer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sublayer(
    request: Request,
    sublayer_id: int,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Мягкое удаление вложенного слоя."""
    sublayer = db.query(SubLayer).filter(SubLayer.id == sublayer_id, SubLayer.is_deleted == False).first()
    if not sublayer:
        raise HTTPException(status_code=404, detail="Вложенный слой не найден")
    
    sublayer_name = sublayer.name
    
    # Мягкое удаление - помечаем слой и все под-вложенные как удалённые
    sublayer.is_deleted = True
    for subsub in sublayer.sub_sub_layers:
        subsub.is_deleted = True
    
    db.commit()
    
    # Логируем
    AuditService(db).log(
        action="DELETE",
        user=current_user,
        entity_type="sub_layer",
        entity_id=sublayer_id,
        entity_name=sublayer_name,
        description=f"Удалён вложенный слой '{sublayer_name}'",
        request=request,
    )
    
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
    request: Request,
    data: SubSubLayerCreate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Создать новый под-вложенный слой (третий уровень)."""
    # Проверка существования родительского вложенного слоя (не удалённого)
    parent = db.query(SubLayer).filter(SubLayer.id == data.parent_sub_layer_id, SubLayer.is_deleted == False).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Родительский вложенный слой не найден")
    
    # Проверка на дубликат названия (среди не удалённых)
    existing = db.query(SubSubLayer).filter(
        SubSubLayer.parent_sub_layer_id == data.parent_sub_layer_id,
        func.lower(SubSubLayer.name) == data.name.lower().strip(),
        SubSubLayer.is_deleted == False
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Под-вложенный слой с таким названием уже существует"
        )
    
    # Получить максимальный order (среди не удалённых)
    max_order = db.query(func.max(SubSubLayer.order)).filter(
        SubSubLayer.parent_sub_layer_id == data.parent_sub_layer_id,
        SubSubLayer.is_deleted == False
    ).scalar() or 0
    
    subsublayer = SubSubLayer(
        name=data.name.strip(),
        parent_sub_layer_id=data.parent_sub_layer_id,
        order=max_order + 1,
    )
    db.add(subsublayer)
    db.commit()
    db.refresh(subsublayer)
    
    # Логируем
    AuditService(db).log(
        action="CREATE",
        user=current_user,
        entity_type="sub_sub_layer",
        entity_id=subsublayer.id,
        entity_name=subsublayer.name,
        description=f"Создан под-вложенный слой '{subsublayer.name}' в слое '{parent.name}'",
        request=request,
    )
    
    return subsublayer


@router.patch("/subsublayers/{subsublayer_id}", response_model=SubSubLayerOut)
def update_subsublayer(
    request: Request,
    subsublayer_id: int,
    data: SubSubLayerUpdate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Обновить под-вложенный слой."""
    subsublayer = db.query(SubSubLayer).filter(SubSubLayer.id == subsublayer_id, SubSubLayer.is_deleted == False).first()
    if not subsublayer:
        raise HTTPException(status_code=404, detail="Под-вложенный слой не найден")
    
    old_name = subsublayer.name
    changes = {}
    
    if data.name is not None:
        # Проверка на дубликат (среди не удалённых)
        existing = db.query(SubSubLayer).filter(
            SubSubLayer.parent_sub_layer_id == subsublayer.parent_sub_layer_id,
            func.lower(SubSubLayer.name) == data.name.lower().strip(),
            SubSubLayer.id != subsublayer_id,
            SubSubLayer.is_deleted == False
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Под-вложенный слой с таким названием уже существует"
            )
        if subsublayer.name != data.name.strip():
            changes["name"] = {"old": subsublayer.name, "new": data.name.strip()}
        subsublayer.name = data.name.strip()
    
    if data.is_visible is not None:
        if subsublayer.is_visible != data.is_visible:
            changes["is_visible"] = {"old": subsublayer.is_visible, "new": data.is_visible}
        subsublayer.is_visible = data.is_visible
    
    if data.order is not None:
        if subsublayer.order != data.order:
            changes["order"] = {"old": subsublayer.order, "new": data.order}
        subsublayer.order = data.order
    
    db.commit()
    db.refresh(subsublayer)
    
    # Логируем
    if changes:
        AuditService(db).log(
            action="UPDATE",
            user=current_user,
            entity_type="sub_sub_layer",
            entity_id=subsublayer.id,
            entity_name=subsublayer.name,
            description=f"Обновлён под-вложенный слой '{old_name}'",
            details={"changes": changes},
            request=request,
        )
    
    return subsublayer


@router.delete("/subsublayers/{subsublayer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subsublayer(
    request: Request,
    subsublayer_id: int,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Мягкое удаление под-вложенного слоя."""
    subsublayer = db.query(SubSubLayer).filter(SubSubLayer.id == subsublayer_id, SubSubLayer.is_deleted == False).first()
    if not subsublayer:
        raise HTTPException(status_code=404, detail="Под-вложенный слой не найден")
    
    subsublayer_name = subsublayer.name
    
    # Мягкое удаление
    subsublayer.is_deleted = True
    db.commit()
    
    # Логируем
    AuditService(db).log(
        action="DELETE",
        user=current_user,
        entity_type="sub_sub_layer",
        entity_id=subsublayer_id,
        entity_name=subsublayer_name,
        description=f"Удалён под-вложенный слой '{subsublayer_name}'",
        request=request,
    )
    
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
