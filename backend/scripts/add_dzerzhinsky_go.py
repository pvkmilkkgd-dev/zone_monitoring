"""Добавить городской округ Дзержинский в Московскую область."""
import os
import uuid
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

with engine.begin() as conn:
    region_id = conn.execute(
        text("SELECT id FROM regions WHERE name = 'Московская область'"),
    ).scalar()
    if not region_id:
        print("Регион «Московская область» не найден.")
        exit(1)

    existing = conn.execute(
        text("""
            SELECT 1 FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name = 'Московская область' AND d.name = 'городской округ Дзержинский'
        """),
    ).scalar()
    if existing:
        print("Запись «городской округ Дзержинский» уже есть в Московской области.")
        exit(0)

    conn.execute(
        text("INSERT INTO districts (id, region_id, name, geom) VALUES (:id, :rid, :name, NULL)"),
        {"id": uuid.uuid4(), "rid": region_id, "name": "городской округ Дзержинский"},
    )
    print("Добавлено: Московская область — городской округ Дзержинский.")
