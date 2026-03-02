import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT d.name, 
               ST_Area(d.geom::geography)/1000000 as area_km2,
               ST_NPoints(d.geom) as npoints
        FROM districts d
        JOIN regions r ON r.id = d.region_id
        WHERE r.name = 'Алтайский край'
        ORDER BY area_km2 DESC
    """)).fetchall()

total_area = 0
print(f"{'Name':<55} {'Area km²':>10} {'Points':>8}")
print("-" * 75)
for name, area, npoints in rows:
    total_area += area
    small = " <-- small?" if area < 50 else ""
    print(f"{name:<55} {area:>10.1f} {npoints:>8}{small}")

print("-" * 75)
print(f"{'TOTAL':<55} {total_area:>10.1f}")
print(f"\nОфициальная площадь Алтайского края: ~167,996 km²")
print(f"Покрытие: {total_area/167996*100:.1f}%")
