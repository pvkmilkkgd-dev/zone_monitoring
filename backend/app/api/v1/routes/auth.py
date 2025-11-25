from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.schemas.user import Token, User

router = APIRouter()


@router.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # TODO: Replace with real user lookup from DB
    fake_user = User(id=1, username=form_data.username, role="admin", hashed_password="")

    # TODO: Store and compare hashed password from DB
    if form_data.password != "password" and not verify_password(
        form_data.password, fake_user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(fake_user.id),
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer", "role": fake_user.role}
