from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.user import User


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ разрешён только администратору системы",
        )
    return user
