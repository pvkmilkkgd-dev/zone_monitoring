from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db  # <-- если у тебя get_db в другом месте, поменяй путь

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/db-whoami")
def db_whoami(db: Session = Depends(get_db)):
    user, dbname = db.execute(text("select current_user, current_database()")).one()
    return {"current_user": user, "current_database": dbname}
