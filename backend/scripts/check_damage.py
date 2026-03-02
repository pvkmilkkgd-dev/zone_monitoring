import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    stats = conn.execute(text("""
        SELECT r.name, COUNT(d.id), COUNT(d.geom)
        FROM regions r LEFT JOIN districts d ON d.region_id = r.id
        GROUP BY r.name ORDER BY r.name
    """)).fetchall()

total_d = total_g = 0
damaged = []
for name, cnt, gcnt in stats:
    total_d += cnt
    total_g += gcnt
    if gcnt < cnt and cnt > 0:
        damaged.append((name, cnt, gcnt))
        print(f"  {cnt:4d} ({gcnt:4d} geom)  {name}")

print(f"\nTotal: {total_d} districts, {total_g} with geometry")
print(f"Regions with missing geometry: {len(damaged)}")
