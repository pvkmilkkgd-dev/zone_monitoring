"""Сириус не входит в Краснодарский край — федеральная территория.

Проверяет БД и при необходимости: создаёт регион «Федеральная территория Сириус»
и переносит туда район «городской округ Сириус».
"""
import os
import uuid
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

REGION_NAME = "Федеральная территория Сириус"

with engine.begin() as conn:
    rows = conn.execute(text("""
        SELECT d.id, d.name, r.name as region_name, r.id as region_id
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name ILIKE '%сириус%'
        ORDER BY r.name, d.name
    """)).fetchall()

    if not rows:
        print("В БД нет записей с 'Сириус'. Менять нечего.")
        exit(0)

    for r in rows:
        print(f"Найдено: {r[1]} в регионе «{r[2]}»")

    # Регион «Федеральная территория Сириус»
    sirius_region_id = conn.execute(
        text("SELECT id FROM regions WHERE name = :name"),
        {"name": REGION_NAME},
    ).scalar()

    if not sirius_region_id:
        sirius_region_id = uuid.uuid4()
        conn.execute(
            text("""
                INSERT INTO regions (id, name, name_original, created_at, updated_at, is_active)
                VALUES (:id, :name, :name_original, NOW(), NOW(), true)
            """),
            {"id": sirius_region_id, "name": REGION_NAME, "name_original": REGION_NAME},
        )
        print(f"\nСоздан регион: «{REGION_NAME}» (id={sirius_region_id})")

    krasnodar_id = conn.execute(text("SELECT id FROM regions WHERE name = 'Краснодарский край'")).scalar()
    for r in rows:
        if str(r[3]) == str(krasnodar_id):
            conn.execute(
                text("UPDATE districts SET region_id = :rid WHERE id = :did"),
                {"rid": sirius_region_id, "did": r[0]},
            )
            print(f"Район «{r[1]}» перенесён из Краснодарского края в «{REGION_NAME}».")
        else:
            print(f"Район «{r[1]}» уже не в Краснодарском крае (регион: {r[2]}).")

print("\nИтог: Сириус в БД привязан к региону «Федеральная территория Сириус», не к Краснодарскому краю.")
