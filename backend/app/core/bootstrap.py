from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User


def require_bootstrap_completed(db: Session = Depends(get_db)) -> None:
    """
    Блокирует доступ к защищённым эндпоинтам,
    если в системе ещё нет ни одного пользователя.
    """
    users_count = db.query(User).count()
    if users_count == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Система не инициализирована. Завершите первичную настройку.",
        )
