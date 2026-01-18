from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base


class AdministrativeZone(Base):
    """Модель для хранения административных зон и отделов."""
    __tablename__ = "administrative_zones"

    id = Column(Integer, primary_key=True, index=True)
    map_id = Column(Integer, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    department_name = Column(String(255), nullable=False, comment="Название отдела")
    district_names = Column(JSON, nullable=False, comment="Список административных районов (JSON массив)")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    map = relationship("Map", back_populates="administrative_zones")
