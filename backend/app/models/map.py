from sqlalchemy import Column, Integer, JSON, String

from app.db.session import Base


class Map(Base):
    __tablename__ = "maps"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    bounds = Column(JSON, nullable=True)

