import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)

with e.connect() as c:
    for city in ['город Москва', 'город Санкт-Петербург', 'город Севастополь']:
        row = c.execute(text("""
            SELECT id, ST_Area(geom::geography)/1e6, ST_NPoints(geom)
            FROM regions WHERE name = :name
        """), {'name': city}).fetchone()
        print(f"\n=== {city} ===")
        if row:
            print(f"  Area: {row[1]:.1f} km2, Points: {row[2]}")
            districts = c.execute(text("""
                SELECT d.name, COALESCE(ST_Area(d.geom::geography)/1e6, 0), ST_NPoints(d.geom)
                FROM districts d WHERE d.region_id = :rid ORDER BY d.name
            """), {'rid': row[0]}).fetchall()
            print(f"  Districts: {len(districts)}")
            for d in districts[:5]:
                print(f"    {d[0]}: {d[1]:.1f} km2")
            if len(districts) > 5:
                print(f"    ... +{len(districts)-5} more")
