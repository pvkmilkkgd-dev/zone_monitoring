"""Перепривязать городской округ Алексин к Тульской области (не Калужской)."""
import os
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

with engine.begin() as conn:
    row = conn.execute(text("""
        SELECT d.id, d.name, r.name as region_name, r.id as region_id
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name = 'городской округ Алексин'
    """)).fetchone()
    if not row:
        print("Район «городской округ Алексин» не найден.")
        exit(1)
    print(f"Сейчас: {row[1]} в регионе «{row[2]}»")

    tula_id = conn.execute(text("SELECT id FROM regions WHERE name = 'Тульская область'")).scalar()
    if not tula_id:
        print("Регион «Тульская область» не найден.")
        exit(1)

    if str(row[3]) == str(tula_id):
        print("Уже привязан к Тульской области.")
        exit(0)

    conn.execute(
        text("UPDATE districts SET region_id = :tid WHERE id = :did"),
        {"tid": tula_id, "did": row[0]},
    )
    print("Обновлено: городской округ Алексин перенесён в Тульскую область.")
