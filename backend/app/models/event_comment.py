from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class EventComment(Base):
    __tablename__ = "event_comments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    text = Column(Text, nullable=False, comment="Текст комментария")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="Мягкое удаление")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    event = relationship("Event", back_populates="comments")
    user = relationship("User", backref="event_comments")
