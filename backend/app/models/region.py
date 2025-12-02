from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    map_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("maps.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)

    highlight_criterion_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("criteria.id"),
        nullable=True,
    )

    highlight_value: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    map: Mapped["Map"] = relationship(
        "Map",
        back_populates="regions",
    )

    highlight_criterion: Mapped["Criterion"] = relationship(
        "Criterion",
        back_populates="regions",
    )

    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="region",
        cascade="all,delete-orphan",
    )
