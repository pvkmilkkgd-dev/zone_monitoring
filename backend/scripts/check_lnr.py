"""Проверить текущий список районов ЛНР в БД."""
import os
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT r.id, r.name, d.name as district_name,
               CASE WHEN d.geom IS NOT NULL THEN ROUND(ST_Area(d.geom::geography)/1000000) ELSE NULL END as area_km2
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name ILIKE '%луган%'
        ORDER BY d.name
    """)).fetchall()

print("Регион и районы ЛНР в БД:")
if rows:
    rid = rows[0][0]
    rname = rows[0][1]
    print(f"Регион: {rname} (id={rid})")
    print(f"Районов: {len(rows)}\n")
    for r in rows:
        a = f" {int(r[3])} km2" if r[3] else ""
        print(f"  {r[2]}{a}")
else:
    print("Регион с 'луган' в названии не найден или нет районов.")
    # list regions with lugh
    r2 = conn.execute(text("SELECT id, name FROM regions WHERE name ILIKE '%луган%'")).fetchall()
    for x in r2:
        print(f"  Регион: {x[1]} (id={x[0]})")
