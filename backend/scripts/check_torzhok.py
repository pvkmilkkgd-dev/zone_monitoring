"""Проверить, что есть в БД по Торжку."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

REGION_NAME = "Тверская область"


def main():
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT d.name FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name LIKE '%Торжок%'
                ORDER BY d.name
            """),
            {"region": REGION_NAME},
        ).fetchall()
        
        print("В БД по Торжку:")
        if rows:
            for r in rows:
                print(f"  - {r[0]}")
        else:
            print("  (не найдено)")


if __name__ == "__main__":
    main()
