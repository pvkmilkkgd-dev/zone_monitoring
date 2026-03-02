"""Диагностика карты ДНР: площади, границы, валидность геометрии."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rid = c.execute(text("SELECT id FROM regions WHERE name = 'Донецкая Народная Республика'")).scalar()
    rows = c.execute(text("""
        SELECT name, ROUND(ST_Area(geom::geography)/1e6) as km2,
               ST_NPoints(geom) as pts,
               ST_IsValid(geom) as valid,
               ST_AsText(ST_Centroid(geom)) as centroid
        FROM districts WHERE region_id = :rid ORDER BY ST_Area(geom::geography) DESC
    """), {'rid': str(rid)}).fetchall()

print("ДНР: площадь, точки, валидность, центр (центроид)\n")
total = 0
for name, km2, pts, valid, cent in rows:
    total += km2 or 0
    print(f"  {km2 or 0:>6} km2  pts={pts or 0:>5}  valid={valid}  {name[:45]}")
    if cent:
        print(f"         centroid: {cent[:60]}")

print(f"\nСуммарная площадь ДНР в базе: {total} km2 (ожид. ~26 500 km2)")
# Проверка: все центроиды должны быть в районе Донбасса (37-39° в.д., 47-48.5° с.ш.)
with e.connect() as c2:
    bad = c2.execute(text("""
        SELECT name FROM districts d
        WHERE region_id = :rid AND geom IS NOT NULL
        AND (ST_X(ST_Centroid(geom)) < 36 OR ST_X(ST_Centroid(geom)) > 40
             OR ST_Y(ST_Centroid(geom)) < 46 OR ST_Y(ST_Centroid(geom)) > 50)
    """), {'rid': str(rid)}).fetchall()
    if bad:
        print("Записи с центроидом вне Донбасса (37-40°E, 46-50°N):", [b[0] for b in bad])
