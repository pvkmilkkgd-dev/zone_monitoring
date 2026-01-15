from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class SystemSettingsResponse(BaseModel):
  id: int
  department_name: Optional[str] = None
  region_ids: List[UUID] = []
  region: Optional[str] = None  # совместимость

  model_config = {"from_attributes": True}


class SystemSettingsUpdate(BaseModel):
  department_name: Optional[str] = None
  region_ids: Optional[List[UUID]] = None
  region: Optional[str] = None  # старое поле

  @field_validator("department_name", mode="before")
  @classmethod
  def empty_str_to_none(cls, v):
    if v is None:
      return None
    if isinstance(v, str):
      v = v.strip()
      return v or None
    return v
