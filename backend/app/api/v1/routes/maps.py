from fastapi import APIRouter, Depends, UploadFile

from app.core.security import require_roles
from app.schemas.map import Map
from app.services.map_service import MapService

router = APIRouter()
service = MapService()


@router.post(
    "/maps/upload",
    response_model=Map,
    dependencies=[Depends(require_roles("admin"))],
)
def upload_map(file: UploadFile):
    # TODO: Persist file storage and metadata
    return service.upload_map(file)


@router.get("/maps/current", response_model=Map | None)
def get_current_map():
    return service.get_current_map()
