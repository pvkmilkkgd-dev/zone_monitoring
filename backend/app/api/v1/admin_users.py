from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.core.security import hash_password, validate_password_strength
from app.models.user import User
from app.schemas.user import (
    UserCreateByAdmin,
    UserPasswordReset,
    UserPublic,
    UserRoleUpdate,
    UserUpdateByAdmin,
)

router = APIRouter(
    prefix="/api/v1/admin/users",
    tags=["admin-users"],
)


@router.get("/", response_model=List[UserPublic])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    users = db.query(User).order_by(User.id.asc()).all()
    return users


@router.post("/", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateByAdmin,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует",
        )
    
    # Валидация пароля
    is_valid, error_msg = validate_password_strength(payload.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserPublic)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    payload: UserUpdateByAdmin,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """Обновить данные пользователя (логин, полное имя)."""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    
    # Обновление логина
    if payload.username is not None and payload.username != user.username:
        existing = db.query(User).filter(User.username == payload.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким логином уже существует",
            )
        user.username = payload.username
    
    # Обновление полного имени
    if payload.full_name is not None:
        user.full_name = payload.full_name
    
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/password", response_model=UserPublic)
def reset_user_password(
    user_id: int,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    
    # Валидация пароля
    is_valid, error_msg = validate_password_strength(payload.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user
