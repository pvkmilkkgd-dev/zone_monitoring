import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    stats = conn.execute(text("""
        SELECT r.name, 
               COUNT(d.id) as total,
               COUNT(d.geom) as with_geom
        FROM regions r
        LEFT JOIN districts d ON d.region_id = r.id
        GROUP BY r.name
        ORDER BY r.name
    """)).fetchall()

total_d = 0
total_g = 0
print(f"{'Region':<55} {'Total':>5} {'Geom':>5}")
print("-" * 70)
for name, cnt, geom_cnt in stats:
    total_d += cnt
    total_g += geom_cnt
    marker = " !!!" if geom_cnt < cnt else ""
    print(f"{name:<55} {cnt:>5} {geom_cnt:>5}{marker}")

print("-" * 70)
print(f"{'TOTAL':<55} {total_d:>5} {total_g:>5}")
print(f"\nRegions: {len(stats)}")
