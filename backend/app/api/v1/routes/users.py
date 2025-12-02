from typing import List

from fastapi import APIRouter, Depends

from app.core.auth import require_role
from app.schemas.user import UserRead

router = APIRouter()


@router.get(
    "/users",
    response_model=List[UserRead],
    dependencies=[Depends(require_role("admin"))],
)
def list_users():
    # TODO: Implement real user listing
    return []
