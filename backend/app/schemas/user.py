from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: str = "operator"
    is_active: bool = True


class UserRead(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UserPublic(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreateByAdmin(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "operator"


class UserRoleUpdate(BaseModel):
    role: str


class UserPasswordReset(BaseModel):
    new_password: str


class UserSelfUpdate(BaseModel):
    username: Optional[str] = Field(None, description="Ваш новый логин")
    current_password: str = Field(..., description="Текущий пароль")
    new_password: Optional[str] = Field(None, description="Новый пароль (если менять)")
