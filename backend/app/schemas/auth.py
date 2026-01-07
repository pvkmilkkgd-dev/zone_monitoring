from pydantic import BaseModel, ConfigDict, constr


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: constr(min_length=3)
    password: constr(min_length=6)
    role: str


class BootstrapAdminCreate(BaseModel):
    """Создание первого администратора системы."""

    username: constr(min_length=3)
    password: constr(min_length=6)


class BootstrapStatus(BaseModel):
    """Статус инициализации системы."""

    needs_bootstrap: bool


class UserMe(BaseModel):
    id: int
    username: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    username: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
