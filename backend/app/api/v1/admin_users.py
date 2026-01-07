from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.core.db import get_db
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import (
    UserCreateByAdmin,
    UserPasswordReset,
    UserPublic,
    UserRoleUpdate,
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

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        role=payload.role,
        is_active=True,
        hashed_password=hash_password(payload.password),
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

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user
