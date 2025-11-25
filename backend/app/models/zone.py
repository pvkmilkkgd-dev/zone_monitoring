from sqlalchemy import Column, Integer, String, Text

from app.db.session import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    polygon = Column(Text, nullable=False)  # TODO: store GeoJSON

