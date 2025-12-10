from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    Token,
    UserCreate,
    BootstrapAdminCreate,
    BootstrapStatus,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# --- Служебное: статус инициализации системы ---


@router.get("/bootstrap-status", response_model=BootstrapStatus)
def get_bootstrap_status(db: Session = Depends(get_db)):
    """Возвращает, нужно ли создавать первого пользователя."""
    count = db.query(User).count()
    return BootstrapStatus(needs_bootstrap=count == 0)


@router.get("/status")
def auth_status(db: Session = Depends(get_db)):
    """Простой статус: есть ли в таблице users хоть один пользователь."""
    has_users = db.query(User).count() > 0
    return {"has_users": has_users}


@router.post("/bootstrap-admin", response_model=Token)
def bootstrap_admin(payload: BootstrapAdminCreate, db: Session = Depends(get_db)):
    """
    Создание первого администратора системы.

    Разрешено только если в таблице users ещё нет ни одной записи.
    """
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Система уже инициализирована. Создание первичного администратора недоступно.",
        )

    user = User(
        username=payload.username,
        role="admin",  # первая учётка всегда администратор
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token, token_type="bearer")


# --- Обычный логин ---


@router.post("/token", response_model=Token)
def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Если система ещё не инициализирована — логиниться нельзя
    if db.query(User).count() == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Система ещё не инициализирована. Создайте администратора на странице первичной настройки.",
        )

    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token, token_type="bearer")


# --- Регистрация можно оставить, но из UI не использовать ---


@router.post("/register", response_model=Token, deprecated=True)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует",
        )

    user = User(
        username=payload.username,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token, token_type="bearer")
