from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, func

from app.db.session import Base


class ZoneState(Base):
    __tablename__ = "zone_states"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    parameters = Column(JSON, nullable=True)
    intensity = Column(String, nullable=True)
    category = Column(String, nullable=True)
    summary_text = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

