from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    map_id = Column(Integer, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    administrative_zone_id = Column(Integer, ForeignKey("administrative_zones.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="ID пользователя создавшего событие")
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="ID пользователя изменившего событие")
    district_name = Column(String(255), nullable=True, comment="Название района где произошло событие")
    status = Column(String(32), nullable=False, default="warning")  # "ok" | "warning" | "alert"
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    importance = Column(Integer, nullable=False, default=5, comment="Коэффициент важности от 1 до 10")
    is_archived = Column(Boolean, nullable=False, default=False, comment="Отметка 'не актуально'")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="Мягкое удаление")
    layer_id = Column(Integer, ForeignKey("layers.id", ondelete="SET NULL"), nullable=True, comment="ID главного слоя")
    sub_layer_id = Column(Integer, ForeignKey("sub_layers.id", ondelete="SET NULL"), nullable=True, comment="ID вложенного слоя")
    sub_sub_layer_id = Column(Integer, ForeignKey("sub_sub_layers.id", ondelete="SET NULL"), nullable=True, comment="ID под-вложенного слоя")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    map = relationship("Map", back_populates="events")
    administrative_zone = relationship("AdministrativeZone", backref="events")
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_events")
    updated_by = relationship("User", foreign_keys=[updated_by_id], backref="updated_events")
    images = relationship("EventImage", back_populates="event", cascade="all, delete-orphan")
    documents = relationship("EventDocument", back_populates="event", cascade="all, delete-orphan")
    comments = relationship("EventComment", back_populates="event", cascade="all, delete-orphan", order_by="EventComment.created_at.desc()")
    layer = relationship("Layer", backref="events")
    sub_layer = relationship("SubLayer", backref="events")
    sub_sub_layer = relationship("SubSubLayer", backref="events")