from typing import Optional

from app.core.security import get_password_hash, verify_password
from app.schemas.user import UserRead


class AuthService:
    def authenticate_user(self, username: str, password: str) -> Optional[UserRead]:
        # TODO: Replace with real user lookup
        fake_hashed = get_password_hash("password")
        if username == "admin" and verify_password(password, fake_hashed):
            return UserRead(id=1, username=username, role="admin")
        return None

    def create_user(self, username: str, password: str, role: str = "viewer") -> UserRead:
        # TODO: Persist user in DB
        get_password_hash(password)
        return UserRead(id=0, username=username, role=role)
