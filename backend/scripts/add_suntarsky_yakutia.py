"""Добавить Сунтарский муниципальный район в Республику Саха (Якутия)."""
import os
import uuid
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

REGION_NAME = "Республика Саха (Якутия)"
DISTRICT_NAME = "Сунтарский муниципальный район"


def main():
    with engine.begin() as conn:
        region_id = conn.execute(
            text("SELECT id FROM regions WHERE name = :name"),
            {"name": REGION_NAME},
        ).scalar()
        if not region_id:
            print(f"Регион «{REGION_NAME}» не найден.")
            return

        exists = conn.execute(
            text("""
                SELECT 1 FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """),
            {"region": REGION_NAME, "name": DISTRICT_NAME},
        ).scalar()
        if exists:
            print(f"Уже есть: {DISTRICT_NAME}")
            return

        conn.execute(
            text("INSERT INTO districts (id, region_id, name, geom) VALUES (:id, :rid, :name, NULL)"),
            {"id": uuid.uuid4(), "rid": region_id, "name": DISTRICT_NAME},
        )
        print(f"Добавлено: «{REGION_NAME}» — «{DISTRICT_NAME}»")


if __name__ == "__main__":
    main()
