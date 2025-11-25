from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class MapBase(BaseModel):
    filename: str
    bounds: Optional[Dict[str, Any]] = None


class MapCreate(MapBase):
    pass


class Map(MapBase):
    id: int | None = None

    model_config = ConfigDict(from_attributes=True)
