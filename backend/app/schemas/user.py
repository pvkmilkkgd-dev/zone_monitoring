from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserBase(BaseModel):
    username: str
    role: str = "viewer"


class UserRead(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UserPublic(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreateByAdmin(BaseModel):
    username: str
    password: str = Field(..., min_length=6, max_length=128)
    full_name: Optional[str] = None
    role: str = "operator"
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        if len(v) > 128:
            raise ValueError('Пароль слишком длинный (максимум 128 символов)')
        return v


class UserRoleUpdate(BaseModel):
    role: str


class UserPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        if len(v) > 128:
            raise ValueError('Пароль слишком длинный (максимум 128 символов)')
        return v


class UserUpdateByAdmin(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None


class UserSelfUpdate(BaseModel):
    username: Optional[str] = Field(None, description="Ваш новый логин")
    current_password: str = Field(..., description="Текущий пароль")
    new_password: Optional[str] = Field(None, min_length=6, max_length=128, description="Новый пароль (если менять)")
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) < 6:
                raise ValueError('Пароль должен содержать минимум 6 символов')
            if len(v) > 128:
                raise ValueError('Пароль слишком длинный (максимум 128 символов)')
        return v
