from pydantic import BaseModel, constr


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
