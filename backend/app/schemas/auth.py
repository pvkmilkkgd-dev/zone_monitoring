from pydantic import BaseModel, Field, validator


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str
    password_confirm: str

    @validator("password_confirm")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Пароли не совпадают")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str
