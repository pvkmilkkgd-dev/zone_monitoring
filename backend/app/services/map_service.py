from typing import Optional

from fastapi import UploadFile

from app.schemas.map import Map


class MapService:
    def upload_map(self, file: UploadFile) -> Map:
        # TODO: Save file to storage and store metadata in DB
        return Map(id=1, filename=file.filename, bounds={"type": "FeatureCollection"})

    def get_current_map(self) -> Optional[Map]:
        # TODO: Retrieve latest uploaded map
        return Map(id=1, filename="current-map.png", bounds={"type": "FeatureCollection"})

