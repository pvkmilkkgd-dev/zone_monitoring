from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from app.core.db import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    region = Column(String(255), nullable=True)
    department_name = Column(String(255), nullable=True)
    region_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SystemSettings id={self.id} region={self.region!r}>"
