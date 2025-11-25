from typing import Optional

from pydantic import BaseModel, ConfigDict


class ZoneBase(BaseModel):
    name: str
    polygon: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Zone A",
                "polygon": '{"type":"Polygon","coordinates":[...]}',  # GeoJSON placeholder
            }
        }
    )


class ZoneCreate(ZoneBase):
    pass


class Zone(ZoneBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
