"""Check NAO vs YANAO districts - they seem mixed up"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

with e.connect() as c:
    # Check NAO
    print("=== Ненецкий АО ===")
    rows = c.execute(text("""
        SELECT d.name, ST_Area(d.geom::geography)/1e6
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Ненецкий автономный округ'
        ORDER BY d.name
    """)).fetchall()
    total = 0
    for r in rows:
        total += r[1] or 0
        print(f"  {r[0]}: {r[1]:.0f} km2")
    print(f"  Total: {total:.0f} km2 (should be ~176,810)")
    
    # Check YANAO
    print("\n=== Ямало-Ненецкий АО ===")
    rows = c.execute(text("""
        SELECT d.name, ST_Area(d.geom::geography)/1e6
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%%Ямало%%'
        ORDER BY d.name
    """)).fetchall()
    total = 0
    for r in rows:
        total += r[1] or 0
        print(f"  {r[0]}: {r[1]:.0f} km2")
    print(f"  Total: {total:.0f} km2 (should be ~769,250)")
    
    # Region areas
    print("\n=== Region areas ===")
    for name in ['Ненецкий автономный округ', 'Ямало-Ненецкий автономный округ']:
        row = c.execute(text("""
            SELECT ST_Area(geom::geography)/1e6 FROM regions WHERE name = :name
        """), {'name': name}).fetchone()
        if row:
            print(f"  {name}: {row[0]:.0f} km2")
