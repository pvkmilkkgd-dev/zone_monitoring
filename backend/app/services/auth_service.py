from typing import Optional

from app.core.security import get_password_hash, verify_password
from app.schemas.user import User


class AuthService:
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        # TODO: Replace with real user lookup
        fake_hashed = get_password_hash("password")
        if username == "admin" and verify_password(password, fake_hashed):
            return User(id=1, username=username, role="admin", hashed_password=fake_hashed)
        return None

    def create_user(self, username: str, password: str, role: str = "viewer") -> User:
        # TODO: Persist user in DB
        hashed = get_password_hash(password)
        return User(id=0, username=username, role=role, hashed_password=hashed)

