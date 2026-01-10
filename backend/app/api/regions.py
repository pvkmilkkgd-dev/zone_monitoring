from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db  # <-- ВАЖНО: путь должен быть таким же, как в maps.py

router = APIRouter(prefix="/api", tags=["regions"])


@router.get("/regions")
def list_regions(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id, name FROM regions ORDER BY name")).all()
    return [{"id": r.id, "name": r.name} for r in rows]
