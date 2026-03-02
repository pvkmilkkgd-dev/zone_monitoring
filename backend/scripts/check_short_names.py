"""Check districts with short names (missing 'муниципальный район', 'городской округ', etc.)"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

with e.connect() as c:
    # Find districts with suspiciously short names (no type prefix/suffix)
    rows = c.execute(text("""
        SELECT d.name, r.name as region_name
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name NOT LIKE '%район%'
          AND d.name NOT LIKE '%округ%'
          AND d.name NOT LIKE '%город%'
          AND d.name NOT LIKE '%ЗАТО%'
          AND d.name NOT LIKE '%поселение%'
        ORDER BY r.name, d.name
    """)).fetchall()

print(f"Districts without type designation ({len(rows)}):")
print(f"{'District':<50} {'Region':<40}")
print("-" * 90)
for r in rows:
    print(f"{r[0]:<50} {r[1]:<40}")

# Also specifically check Arkhangelsk
print(f"\n\n=== All Arkhangelsk Oblast districts ===")
rows2 = c.execute(text("""
    SELECT d.name
    FROM districts d
    JOIN regions r ON d.region_id = r.id
    WHERE r.name = 'Архангельская область'
    ORDER BY d.name
""")).fetchall()
for r in rows2:
    print(f"  {r[0]}")
