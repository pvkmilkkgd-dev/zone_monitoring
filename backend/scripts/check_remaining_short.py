import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, r.name
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE d.name NOT LIKE '%%район%%' AND d.name NOT LIKE '%%округ%%'
          AND d.name NOT LIKE '%%город%%' AND d.name NOT LIKE '%%ЗАТО%%'
          AND d.name NOT LIKE '%%поселение%%' AND d.name NOT LIKE '%%улус%%'
          AND d.name NOT LIKE '%%участок%%' AND d.name NOT LIKE '%%кожуун%%'
          AND d.name NOT LIKE '%%образование%%'
        ORDER BY r.name
    """)).fetchall()
print(f"Still without type designation: {len(rows)}")
for r in rows:
    print(f"  {r[0]} ({r[1]})")
