from typing import List

from fastapi import APIRouter, Depends

from app.core.security import get_current_user, require_roles
from app.schemas.zone import Zone, ZoneCreate
from app.services.zone_service import ZoneService

router = APIRouter()
service = ZoneService()


@router.get(
    "/zones",
    response_model=List[Zone],
    dependencies=[Depends(get_current_user)],
)
def list_zones():
    # TODO: Fetch zones from DB
    return service.list_zones()


@router.get(
    "/zones/{zone_id}",
    response_model=Zone,
    dependencies=[Depends(get_current_user)],
)
def get_zone(zone_id: int):
    return service.get_zone(zone_id)


@router.post(
    "/zones/{zone_id}/state",
    dependencies=[Depends(require_roles("admin", "editor"))],
)
def update_zone_state(zone_id: int, data: dict):
    # TODO: Validate schema and persist updates
    return service.update_zone_state(zone_id, data)
