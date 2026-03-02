import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
regions = ['Краснодарский край', 'Красноярский край', 'Приморский край',
           'Ставропольский край', 'Хабаровский край', 'Амурская область']

with engine.connect() as conn:
    for rname in regions:
        rows = conn.execute(text("""
            SELECT d.name, d.geom IS NOT NULL, ST_Area(d.geom::geography)/1000000
            FROM districts d JOIN regions r ON r.id = d.region_id
            WHERE r.name = :rname ORDER BY d.name
        """), {"rname": rname}).fetchall()
        
        print(f"\n{rname}: {len(rows)} districts")
        no_geom = [r[0] for r in rows if not r[1]]
        small = [r[0] for r in rows if r[1] and r[2] < 1]
        if no_geom:
            print(f"  No geometry: {no_geom[:5]}")
        if small:
            print(f"  Small area (<1km²): {small[:5]}")
        # Show first 5
        for name, has_geom, area in rows[:5]:
            print(f"  {name} {'OK' if has_geom else 'NO GEOM'} {area:.0f}km²")
