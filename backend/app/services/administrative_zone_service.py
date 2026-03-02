from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.administrative_zone import AdministrativeZone
from app.schemas.administrative_zone import AdministrativeZoneCreate, AdministrativeZoneUpdate


class AdministrativeZoneService:
    """Сервис для управления административными зонами."""
    
    def __init__(self, db: Session):
        self.db = db

    def list_zones(self, map_id: Optional[int] = None) -> List[AdministrativeZone]:
        """Получить список всех административных зон или по конкретной карте (без удалённых)."""
        query = self.db.query(AdministrativeZone).filter(AdministrativeZone.is_deleted == False)
        if map_id:
            query = query.filter(AdministrativeZone.map_id == map_id)
        return query.order_by(AdministrativeZone.id.desc()).all()

    def get_zone(self, zone_id: int) -> Optional[AdministrativeZone]:
        """Получить административную зону по ID (не удалённую)."""
        return self.db.query(AdministrativeZone).filter(
            AdministrativeZone.id == zone_id,
            AdministrativeZone.is_deleted == False
        ).first()

    def create_zone(self, zone_data: AdministrativeZoneCreate) -> AdministrativeZone:
        """Создать новую административную зону."""
        zone = AdministrativeZone(
            map_id=zone_data.map_id,
            department_name=zone_data.department_name,
            description=zone_data.description,
            district_names=zone_data.district_names,
            layer_id=zone_data.layer_id,
            sub_layer_id=zone_data.sub_layer_id,
            sub_sub_layer_id=zone_data.sub_sub_layer_id,
        )
        self.db.add(zone)
        self.db.commit()
        self.db.refresh(zone)
        return zone

    def update_zone(
        self, zone_id: int, zone_data: AdministrativeZoneUpdate
    ) -> Optional[AdministrativeZone]:
        """Обновить административную зону."""
        zone = self.get_zone(zone_id)
        if not zone:
            return None
        
        update_data = zone_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(zone, field, value)
        
        self.db.commit()
        self.db.refresh(zone)
        return zone

    def delete_zone(self, zone_id: int) -> bool:
        """Мягкое удаление административной зоны."""
        zone = self.get_zone(zone_id)
        if not zone:
            return False
        
        # Мягкое удаление
        zone.is_deleted = True
        self.db.commit()
        return True
