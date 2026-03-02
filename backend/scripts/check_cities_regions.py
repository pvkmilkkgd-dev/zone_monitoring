"""Check city-regions: Moscow, SPb, Sevastopol"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

with e.connect() as c:
    for city in ['Москва', 'Санкт-Петербург', 'Севастополь']:
        print(f"\n=== {city} ===")
        row = c.execute(text("""
            SELECT id, ST_Area(geom::geography)/1e6, ST_NPoints(geom)
            FROM regions WHERE name = :name
        """), {'name': city}).fetchone()
        if row:
            print(f"  Region: area={row[1]:.1f} km2, pts={row[2]}")
            
            districts = c.execute(text("""
                SELECT d.name, ST_Area(d.geom::geography)/1e6, ST_NPoints(d.geom)
                FROM districts d WHERE d.region_id = :rid
                ORDER BY d.name
            """), {'rid': row[0]}).fetchall()
            print(f"  Districts: {len(districts)}")
            for d in districts[:10]:
                print(f"    {d[0]}: {d[1]:.1f} km2, {d[2]} pts")
            if len(districts) > 10:
                print(f"    ... and {len(districts)-10} more")
        else:
            print(f"  NOT FOUND in DB!")
    
    # Also check Krasnoyarsk
    print(f"\n=== Красноярский край ===")
    row = c.execute(text("""
        SELECT ST_YMin(geom), ST_YMax(geom), ST_XMin(geom), ST_XMax(geom),
               ST_Area(geom::geography)/1e6
        FROM regions WHERE name LIKE '%%Красноярский%%'
    """)).fetchone()
    if row:
        print(f"  Lat: {row[0]:.1f} - {row[1]:.1f}")
        print(f"  Lon: {row[2]:.1f} - {row[3]:.1f}")
        print(f"  Area: {row[4]:.0f} km2")
