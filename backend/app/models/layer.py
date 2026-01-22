from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Layer(Base):
    __tablename__ = "layers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    map_id = Column(Integer, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    is_visible = Column(Boolean, nullable=False, default=True)
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    map = relationship("Map", backref="layers")
    sub_layers = relationship("SubLayer", back_populates="parent_layer", cascade="all, delete-orphan", order_by="SubLayer.order")


class SubLayer(Base):
    __tablename__ = "sub_layers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    parent_layer_id = Column(Integer, ForeignKey("layers.id", ondelete="CASCADE"), nullable=False)
    is_visible = Column(Boolean, nullable=False, default=True)
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    parent_layer = relationship("Layer", back_populates="sub_layers")
    sub_sub_layers = relationship("SubSubLayer", back_populates="parent_sub_layer", cascade="all, delete-orphan", order_by="SubSubLayer.order")


class SubSubLayer(Base):
    __tablename__ = "sub_sub_layers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    parent_sub_layer_id = Column(Integer, ForeignKey("sub_layers.id", ondelete="CASCADE"), nullable=False)
    is_visible = Column(Boolean, nullable=False, default=True)
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    parent_sub_layer = relationship("SubLayer", back_populates="sub_sub_layers")
