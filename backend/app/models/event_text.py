from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EventText(Base):
    __tablename__ = "event_texts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(5), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    event: Mapped["Event"] = relationship(
        "Event",
        back_populates="texts",
    )
