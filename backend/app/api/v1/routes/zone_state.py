from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.schemas.zone_state import ZoneState
from app.services.zone_service import ZoneService

router = APIRouter()
service = ZoneService()


@router.get(
    "/zones/{zone_id}/state",
    response_model=ZoneState,
    dependencies=[Depends(require_roles("admin", "editor", "viewer"))],
)
def get_zone_state(zone_id: int):
    return service.get_zone_state(zone_id)
