from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.schemas.administrative_zone import (
    AdministrativeZone,
    AdministrativeZoneCreate,
    AdministrativeZoneUpdate,
)
from app.services.administrative_zone_service import AdministrativeZoneService

router = APIRouter()


@router.get(
    "/administrative-zones",
    response_model=List[AdministrativeZone],
    dependencies=[Depends(get_current_user)],
)
def list_administrative_zones(
    map_id: Optional[int] = Query(None, description="Фильтр по ID карты"),
    db: Session = Depends(get_db),
):
    """Получить список всех административных зон."""
    service = AdministrativeZoneService(db)
    return service.list_zones(map_id=map_id)


@router.get(
    "/administrative-zones/{zone_id}",
    response_model=AdministrativeZone,
    dependencies=[Depends(get_current_user)],
)
def get_administrative_zone(zone_id: int, db: Session = Depends(get_db)):
    """Получить административную зону по ID."""
    service = AdministrativeZoneService(db)
    zone = service.get_zone(zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Administrative zone with id {zone_id} not found",
        )
    return zone


@router.post(
    "/administrative-zones",
    response_model=AdministrativeZone,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("admin", "editor"))],
)
def create_administrative_zone(
    zone_data: AdministrativeZoneCreate,
    db: Session = Depends(get_db),
):
    """Создать новую административную зону (только для редакторов и администраторов)."""
    service = AdministrativeZoneService(db)
    return service.create_zone(zone_data)


@router.put(
    "/administrative-zones/{zone_id}",
    response_model=AdministrativeZone,
    dependencies=[Depends(require_roles("admin", "editor"))],
)
def update_administrative_zone(
    zone_id: int,
    zone_data: AdministrativeZoneUpdate,
    db: Session = Depends(get_db),
):
    """Обновить административную зону (только для редакторов и администраторов)."""
    service = AdministrativeZoneService(db)
    zone = service.update_zone(zone_id, zone_data)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Administrative zone with id {zone_id} not found",
        )
    return zone


@router.delete(
    "/administrative-zones/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("admin", "editor"))],
)
def delete_administrative_zone(zone_id: int, db: Session = Depends(get_db)):
    """Удалить административную зону (только для редакторов и администраторов)."""
    service = AdministrativeZoneService(db)
    success = service.delete_zone(zone_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Administrative zone with id {zone_id} not found",
        )
