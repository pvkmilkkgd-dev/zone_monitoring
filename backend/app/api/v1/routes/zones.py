from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, require_roles
from app.schemas.zone import Zone, ZoneCreate
from app.schemas.zone_state import ZoneStateCreate, ZoneState
from app.services.zone_service import ZoneService

router = APIRouter()
service = ZoneService()


@router.get(
    "/zones",
    response_model=List[Zone],
    dependencies=[Depends(get_current_user)],
)
def list_zones():
    """Получить список всех зон."""
    return service.list_zones()


@router.get(
    "/zones/{zone_id}",
    response_model=Zone,
    dependencies=[Depends(get_current_user)],
)
def get_zone(zone_id: int):
    """Получить зону по ID."""
    zone = service.get_zone(zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with id {zone_id} not found"
        )
    return zone


@router.post(
    "/zones/{zone_id}/state",
    response_model=ZoneState,
    dependencies=[Depends(require_roles("admin", "editor"))],
)
def update_zone_state(zone_id: int, data: ZoneStateCreate):
    """Обновить состояние зоны (только для редакторов и администраторов)."""
    return service.update_zone_state(zone_id, data.model_dump())
