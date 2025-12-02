from __future__ import annotations

from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Criterion(Base):
    __tablename__ = "criteria"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    regions: Mapped[list["Region"]] = relationship(
        "Region",
        back_populates="highlight_criterion",
    )

    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="criterion",
    )
