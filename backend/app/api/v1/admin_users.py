from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
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
from app.services.audit_service import AuditService

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
    request: Request,
    payload: UserCreateByAdmin,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
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
    
    # Логируем
    AuditService(db).log(
        action="CREATE",
        user=current_admin,
        entity_type="user",
        entity_id=user.id,
        entity_name=user.username,
        description=f"Создан пользователь '{user.username}' с ролью '{user.role}'",
        details={"role": user.role, "full_name": user.full_name},
        request=request,
    )
    
    return user


@router.patch("/{user_id}/role", response_model=UserPublic)
def update_user_role(
    request: Request,
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )

    old_role = user.role
    user.role = payload.role
    db.commit()
    db.refresh(user)
    
    # Логируем
    AuditService(db).log(
        action="UPDATE",
        user=current_admin,
        entity_type="user",
        entity_id=user.id,
        entity_name=user.username,
        description=f"Изменена роль пользователя '{user.username}': {old_role} → {payload.role}",
        details={"old_role": old_role, "new_role": payload.role},
        request=request,
    )
    
    return user


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    request: Request,
    user_id: int,
    payload: UserUpdateByAdmin,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """Обновить данные пользователя (логин, полное имя)."""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    
    old_username = user.username
    changes = {}
    
    # Обновление логина
    if payload.username is not None and payload.username != user.username:
        existing = db.query(User).filter(User.username == payload.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким логином уже существует",
            )
        changes["username"] = {"old": user.username, "new": payload.username}
        user.username = payload.username
    
    # Обновление полного имени
    if payload.full_name is not None:
        if user.full_name != payload.full_name:
            changes["full_name"] = {"old": user.full_name, "new": payload.full_name}
        user.full_name = payload.full_name
    
    db.commit()
    db.refresh(user)
    
    # Логируем
    if changes:
        AuditService(db).log(
            action="UPDATE",
            user=current_admin,
            entity_type="user",
            entity_id=user.id,
            entity_name=user.username,
            description=f"Обновлены данные пользователя '{old_username}'",
            details={"changes": changes},
            request=request,
        )
    
    return user


@router.patch("/{user_id}/password", response_model=UserPublic)
def reset_user_password(
    request: Request,
    user_id: int,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
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
    
    # Логируем
    AuditService(db).log(
        action="UPDATE",
        user=current_admin,
        entity_type="user",
        entity_id=user.id,
        entity_name=user.username,
        description=f"Сброшен пароль пользователя '{user.username}'",
        request=request,
    )
    
    return user
