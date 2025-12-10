from typing import List

from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.schemas.user import UserRead

router = APIRouter()


@router.get(
    "/users",
    response_model=List[UserRead],
    dependencies=[Depends(require_roles("admin"))],
)
def list_users():
    # TODO: Implement real user listing
    return []
