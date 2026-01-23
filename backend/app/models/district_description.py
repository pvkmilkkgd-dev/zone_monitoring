from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.db.base import Base


class DistrictDescription(Base):
    """Модель для хранения описаний районов."""
    __tablename__ = "district_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    district_name = Column(String(255), nullable=False, unique=True, index=True, comment="Название района")
    description = Column(Text, nullable=True, comment="Описание района")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
