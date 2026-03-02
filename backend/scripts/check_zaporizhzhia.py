"""Check Zaporizhzhia Oblast districts in DB."""
import os
import sqlalchemy as sa
from sqlalchemy import text

# Prefer .env
db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT d.id, d.name, d.region_id,
               CASE WHEN d.geom IS NOT NULL THEN ROUND(ST_Area(d.geom::geography)/1000000) ELSE NULL END as area_km2
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name ILIKE '%запорож%'
        ORDER BY d.name
    """)).fetchall()

print("Region: Запорожская область")
print(f"Districts in DB: {len(rows)}\n")
for r in rows:
    area = f" {int(r[3])} km2" if r[3] else " (no geom)"
    print(f"  {r[1]}{area}")
