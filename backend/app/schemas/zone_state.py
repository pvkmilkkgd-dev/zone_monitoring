from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ZoneStateBase(BaseModel):
    zone_id: int
    parameters: Optional[Dict[str, Any]] = None
    intensity: Optional[str] = None
    category: Optional[str] = None
    summary_text: Optional[str] = None


class ZoneStateCreate(ZoneStateBase):
    pass


class ZoneState(ZoneStateBase):
    id: int | None = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
