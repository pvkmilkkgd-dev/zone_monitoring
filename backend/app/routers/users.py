from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserRead, UserPublic, UserSelfUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/me", response_model=UserRead)
def update_me(
    payload: UserSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Текущий пароль указан неверно",
        )

    # Проверяем, что указано хотя бы одно поле для изменения
    username_changed = payload.username and payload.username != current_user.username
    password_changed = bool(payload.new_password)
    
    if not username_changed and not password_changed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать хотя бы одно поле для изменения (username или new_password)",
        )

    if username_changed:
        existing = db.query(User).filter(User.username == payload.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким логином уже существует",
            )
        current_user.username = payload.username

    if password_changed and payload.new_password:
        current_user.password_hash = hash_password(payload.new_password)

    db.commit()
    db.refresh(current_user)

    return current_user
