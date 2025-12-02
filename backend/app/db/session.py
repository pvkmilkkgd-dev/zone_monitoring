from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

Base = declarative_base()

engine = create_engine(
    settings.DATABASE_URL,
    future=True,
    echo=False,  # set to True for SQL debug logs
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def get_db():
    """FastAPI dependency that yields a scoped session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
