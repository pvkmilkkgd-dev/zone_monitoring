from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.administrative_zone import (
    AdministrativeZone,
    AdministrativeZoneCreate,
    AdministrativeZoneUpdate,
)
from app.services.administrative_zone_service import AdministrativeZoneService
from app.services.audit_service import AuditService

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
)
def create_administrative_zone(
    request: Request,
    zone_data: AdministrativeZoneCreate,
    current_user: User = Depends(require_roles("admin", "editor")),
    db: Session = Depends(get_db),
):
    """Создать новую административную зону (только для редакторов и администраторов)."""
    service = AdministrativeZoneService(db)
    zone = service.create_zone(zone_data)
    
    # Логируем
    AuditService(db).log(
        action="CREATE",
        user=current_user,
        entity_type="zone",
        entity_id=zone.id,
        entity_name=zone.department_name,
        description=f"Создано подразделение '{zone.department_name}'",
        details={"district_names": zone.district_names},
        request=request,
    )
    
    return zone


@router.put(
    "/administrative-zones/{zone_id}",
    response_model=AdministrativeZone,
)
def update_administrative_zone(
    request: Request,
    zone_id: int,
    zone_data: AdministrativeZoneUpdate,
    current_user: User = Depends(require_roles("admin", "editor")),
    db: Session = Depends(get_db),
):
    """Обновить административную зону (только для редакторов и администраторов)."""
    service = AdministrativeZoneService(db)
    old_zone = service.get_zone(zone_id)
    old_name = old_zone.department_name if old_zone else None
    
    zone = service.update_zone(zone_id, zone_data)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Administrative zone with id {zone_id} not found",
        )
    
    # Логируем
    AuditService(db).log(
        action="UPDATE",
        user=current_user,
        entity_type="zone",
        entity_id=zone.id,
        entity_name=zone.department_name,
        description=f"Обновлено подразделение '{old_name}'",
        details={"new_data": zone_data.model_dump(exclude_unset=True)},
        request=request,
    )
    
    return zone


@router.delete(
    "/administrative-zones/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_administrative_zone(
    request: Request,
    zone_id: int,
    current_user: User = Depends(require_roles("admin", "editor")),
    db: Session = Depends(get_db),
):
    """Удалить административную зону (только для редакторов и администраторов)."""
    service = AdministrativeZoneService(db)
    zone = service.get_zone(zone_id)
    zone_name = zone.department_name if zone else f"ID:{zone_id}"
    
    success = service.delete_zone(zone_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Administrative zone with id {zone_id} not found",
        )
    
    # Логируем
    AuditService(db).log(
        action="DELETE",
        user=current_user,
        entity_type="zone",
        entity_id=zone_id,
        entity_name=zone_name,
        description=f"Удалено подразделение '{zone_name}'",
        request=request,
    )