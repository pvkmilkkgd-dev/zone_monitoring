"""Удалить Сириус из БД: район и регион «Федеральная территория Сириус»."""
import os
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

with engine.begin() as conn:
    # Удалить район(ы) с Сириус в названии (в любом регионе)
    deleted_d = conn.execute(text("""
        DELETE FROM districts d
        WHERE d.name ILIKE '%сириус%'
        RETURNING d.id, d.name
    """)).fetchall()
    for r in deleted_d:
        print(f"Удалён район: {r[1]}")

    # Удалить регион «Федеральная территория Сириус»
    deleted_r = conn.execute(text("""
        DELETE FROM regions
        WHERE name = 'Федеральная территория Сириус'
        RETURNING id, name
    """)).fetchall()
    for r in deleted_r:
        print(f"Удалён регион: {r[1]}")

    if not deleted_d and not deleted_r:
        print("Записей с Сириус в БД не найдено.")
