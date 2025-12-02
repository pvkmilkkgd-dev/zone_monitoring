from pydantic import BaseModel, ConfigDict, constr


class UserCreate(BaseModel):
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=6, max_length=128)


class UserRead(BaseModel):
    id: int
    username: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str | None = None
