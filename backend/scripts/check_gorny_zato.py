"""Проверить и исправить привязку ЗАТО поселок Горный к Забайкальскому краю."""
import os
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

with engine.connect() as conn:
    # Найти район с "Горный" в названии
    rows = conn.execute(text("""
        SELECT d.id, d.name, r.name as region_name, r.id as region_id
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name ILIKE '%горн%' AND (d.name ILIKE '%зато%' OR d.name ILIKE '%горный%')
        ORDER BY r.name, d.name
    """)).fetchall()
    print("Найденные районы с 'Горный' / ЗАТО:")
    for r in rows:
        print(f"  id={r[0]}, name={r[1]}, region={r[2]}")

    # Также поиск просто "Горный"
    rows2 = conn.execute(text("""
        SELECT d.id, d.name, r.name as region_name
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name ILIKE '%горный%'
        ORDER BY r.name, d.name
    """)).fetchall()
    print("\nВсе районы с 'Горный' в названии:")
    for r in rows2:
        print(f"  {r[1]} | {r[2]}")

    # Районы Камчатского края (нет ли там Горного)
    rows3 = conn.execute(text("""
        SELECT d.name FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name ILIKE '%Камчат%'
        ORDER BY d.name
    """)).fetchall()
    print("\nРайоны в Камчатском крае:")
    for r in rows3:
        print(f"  {r[0]}")
