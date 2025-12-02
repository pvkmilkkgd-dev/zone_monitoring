from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

router = APIRouter(tags=["auth"])

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 512


# ---------- Политика паролей ----------


def validate_password(password: str) -> None:
    f"""Password policy:
    - minimum {MIN_PASSWORD_LENGTH} characters
    - maximum {MAX_PASSWORD_LENGTH} characters
    - at least one lowercase letter
    - at least one uppercase letter
    - at least one digit
    - at least one special character"""
    errors: list[str] = []

    if len(password) > MAX_PASSWORD_LENGTH:
        errors.append(f'Length exceeds {MAX_PASSWORD_LENGTH} characters')
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f'Length is less than {MIN_PASSWORD_LENGTH} characters')
    if not any(c.islower() for c in password):
        errors.append('No lowercase letters')
    if not any(c.isupper() for c in password):
        errors.append('No uppercase letters')
    if not any(c.isdigit() for c in password):
        errors.append('No digits')
    if not any(c in "!@#$%^&*()-_=+[]{};:,.<>/?\\|`~" for c in password):
        errors.append('No special characters')

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Password does not meet security policy: ' + ', '.join(errors),
        )

# ---------- Вспомогательное: текущий пользователь по токену ----------


# ---------- Маршруты ----------


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    # Проверяем, что такого пользователя ещё нет
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует",
        )

    # Проверяем политику пароля
    validate_password(payload.password)

    user = User(
        username=payload.username,
        role="editor",
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": f"Пользователь {user.username} успешно зарегистрирован"}


# JSON-логин для фронтенда
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )

    token = create_access_token(
        {"sub": user.username, "role": user.role}
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        role=user.role,
    )


# Формат для Swagger / OAuth2 (форма x-www-form-urlencoded)
@router.post("/token", response_model=TokenResponse)
def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
        )

    token = create_access_token(
        {"sub": user.username, "role": user.role}
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        role=user.role,
    )



