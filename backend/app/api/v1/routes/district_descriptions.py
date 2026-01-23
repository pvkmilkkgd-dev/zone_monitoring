from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.district_description import DistrictDescription
from app.schemas.district_description import (
    DistrictDescription as DistrictDescriptionSchema,
    DistrictDescriptionCreate,
    DistrictDescriptionUpdate,
)
from app.core.security import require_roles

router = APIRouter()


@router.get("", response_model=List[DistrictDescriptionSchema])
def list_district_descriptions(
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles("admin", "editor", "editor_plus")),
):
    """Получить все описания районов."""
    return db.query(DistrictDescription).all()


@router.get("/{district_name}", response_model=Optional[DistrictDescriptionSchema])
def get_district_description(
    district_name: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles("admin", "editor", "editor_plus")),
):
    """Получить описание района по имени."""
    desc = db.query(DistrictDescription).filter(
        DistrictDescription.district_name == district_name
    ).first()
    return desc


@router.post("", response_model=DistrictDescriptionSchema)
def create_or_update_district_description(
    payload: DistrictDescriptionCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles("admin", "editor", "editor_plus")),
):
    """Создать или обновить описание района."""
    existing = db.query(DistrictDescription).filter(
        DistrictDescription.district_name == payload.district_name
    ).first()
    
    if existing:
        existing.description = payload.description
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_desc = DistrictDescription(
            district_name=payload.district_name,
            description=payload.description,
        )
        db.add(new_desc)
        db.commit()
        db.refresh(new_desc)
        return new_desc


@router.put("/{district_name}", response_model=DistrictDescriptionSchema)
def update_district_description(
    district_name: str,
    payload: DistrictDescriptionUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles("admin", "editor", "editor_plus")),
):
    """Обновить описание района."""
    desc = db.query(DistrictDescription).filter(
        DistrictDescription.district_name == district_name
    ).first()
    
    if not desc:
        # Создаем новую запись
        desc = DistrictDescription(
            district_name=district_name,
            description=payload.description,
        )
        db.add(desc)
    else:
        desc.description = payload.description
    
    db.commit()
    db.refresh(desc)
    return desc


@router.delete("/{district_name}")
def delete_district_description(
    district_name: str,
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles("admin")),
):
    """Удалить описание района."""
    desc = db.query(DistrictDescription).filter(
        DistrictDescription.district_name == district_name
    ).first()
    
    if desc:
        db.delete(desc)
        db.commit()
    
    return {"ok": True}
