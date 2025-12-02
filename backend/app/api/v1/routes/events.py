from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.models.event import Event


router = APIRouter(prefix="/events", tags=["events"])


class EventOut(BaseModel):
    id: int
    map_name: str
    zone_name: str
    status: str
    title: str
    description: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[EventOut])
def list_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    events = (
        db.query(Event)
        .join(Event.map)
        .join(Event.zone)
        .order_by(Event.created_at.desc())
        .limit(100)
        .all()
    )

    result: List[EventOut] = []
    for ev in events:
        result.append(
            EventOut(
                id=ev.id,
                map_name=ev.map.name if ev.map else "",
                zone_name=ev.zone.name if ev.zone else "",
                status=ev.status,
                title=ev.title,
                description=ev.description or "",
                created_at=ev.created_at.strftime("%Y-%m-%d %H:%M"),
            )
        )

    return result
