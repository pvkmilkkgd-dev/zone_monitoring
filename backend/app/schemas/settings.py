from pydantic import BaseModel


class SystemSettingsBase(BaseModel):
    region: str | None = None
    department_name: str | None = None


class SystemSettingsResponse(SystemSettingsBase):
    id: int

    class Config:
        from_attributes = True


class SystemSettingsUpdate(SystemSettingsBase):
    pass
