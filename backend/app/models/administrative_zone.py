from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class AdministrativeZone(Base):
    """Модель для хранения административных зон и отделов."""
    __tablename__ = "administrative_zones"

    id = Column(Integer, primary_key=True, index=True)
    map_id = Column(Integer, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    department_name = Column(String(255), nullable=False, comment="Название отдела")
    district_names = Column(JSON, nullable=False, comment="Список административных районов (JSON массив)")
    layer_id = Column(Integer, ForeignKey("layers.id", ondelete="SET NULL"), nullable=True, comment="ID главного слоя")
    sub_layer_id = Column(Integer, ForeignKey("sub_layers.id", ondelete="SET NULL"), nullable=True, comment="ID вложенного слоя")
    sub_sub_layer_id = Column(Integer, ForeignKey("sub_sub_layers.id", ondelete="SET NULL"), nullable=True, comment="ID под-вложенного слоя")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    map = relationship("Map", back_populates="administrative_zones")
    layer = relationship("Layer", backref="administrative_zones")
    sub_layer = relationship("SubLayer", backref="administrative_zones")
    sub_sub_layer = relationship("SubSubLayer", backref="administrative_zones")
