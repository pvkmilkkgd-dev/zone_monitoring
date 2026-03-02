"""Диагностика карты Санкт-Петербурга: как для Москвы."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.connect() as c:
    # Регион СПб
    row = c.execute(text("""
        SELECT id, name FROM regions 
        WHERE name ILIKE '%санкт%петербург%' OR name ILIKE '%петербург%'
    """)).fetchone()
    if not row:
        print("Регион Санкт-Петербург не найден")
        sys.exit(1)
    rid, rname = row
    rid = str(rid)
    print(f"Регион: {rname} (id={rid})\n")

    # Районы: имя, площадь, точки
    rows = c.execute(text("""
        SELECT name, ROUND(ST_Area(geom::geography)/1e6) as km2, ST_NPoints(geom) as pts
        FROM districts WHERE region_id = :rid
        ORDER BY ST_Area(geom::geography) DESC NULLS LAST
    """), {'rid': rid}).fetchall()

    total = len(rows)
    total_area = sum(r[1] or 0 for r in rows)
    # СПб город ~1439 км² (с пригородами), в границах города ~600-700
    print(f"Районов: {total}")
    print(f"Суммарная площадь: {total_area} km2 (СПб город ~1439 km2, в границах 2024 ~1400)\n")

    print("Топ-15 по площади:")
    for name, km2, pts in rows[:15]:
        ok = "OK" if (pts or 0) > 0 else "NO GEOM"
        print(f"  {km2 or 0} km2  {pts or 0} pts  [{ok}]  {name}")

    print("\nМинимальные по площади:")
    for name, km2, pts in rows[-15:] if len(rows) >= 15 else rows:
        ok = "OK" if (pts or 0) > 0 else "NO GEOM"
        print(f"  {km2 or 0} km2  {pts or 0} pts  [{ok}]  {name}")

    zero_geom = [r[0] for r in rows if (r[1] or 0) == 0 or (r[2] or 0) == 0]
    if zero_geom:
        print(f"\nБез геометрии или 0 площади: {len(zero_geom)} — {zero_geom[:10]}")
