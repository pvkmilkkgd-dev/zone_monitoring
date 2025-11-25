from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    username: str
    role: str = "viewer"


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    hashed_password: str = ""

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = None
