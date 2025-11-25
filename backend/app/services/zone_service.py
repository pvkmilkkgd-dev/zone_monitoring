from typing import Any, Dict, List

from app.schemas.zone import Zone
from app.schemas.zone_state import ZoneState


class ZoneService:
    def list_zones(self) -> List[Zone]:
        # TODO: Replace with DB query returning GeoJSON polygons
        return [
            Zone(id=1, name="Zone A", polygon='{"type":"Polygon","coordinates":[...]}'),
            Zone(id=2, name="Zone B", polygon='{"type":"Polygon","coordinates":[...]}'),
        ]

    def get_zone(self, zone_id: int) -> Zone:
        # TODO: Fetch a zone by id
        return Zone(id=zone_id, name=f"Zone {zone_id}", polygon="{}")

    def update_zone_state(self, zone_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Persist zone state updates for editors/admins
        return {"zone_id": zone_id, "updated": True, "payload": data}

    def get_zone_state(self, zone_id: int) -> ZoneState:
        # TODO: Fetch latest state for viewers
        return ZoneState(
            zone_id=zone_id,
            parameters={"temperature": "N/A"},
            intensity="medium",
            category="info",
            summary_text="Zone status summary",
        )

