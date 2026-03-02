"""Check Sverdlovsk region districts."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Get region
    region = conn.execute(text("""
        SELECT id, name FROM regions WHERE name LIKE '%Свердлов%'
    """)).fetchone()
    
    if not region:
        print("Region not found!")
        sys.exit(1)
    
    print(f"Region: {region[1]}")
    print(f"ID: {region[0]}")
    
    # Count districts
    stats = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN geom IS NOT NULL THEN 1 ELSE 0 END) as with_geom
        FROM districts
        WHERE region_id = :rid
    """), {"rid": str(region[0])}).fetchone()
    
    print(f"\nDistricts: {stats[0]} total, {stats[1]} with geometry")
    
    # List all districts
    districts = conn.execute(text("""
        SELECT name, 
               CASE WHEN geom IS NOT NULL THEN 'YES' ELSE 'NO' END as has_geom,
               ST_NPoints(geom) as points
        FROM districts
        WHERE region_id = :rid
        ORDER BY name
    """), {"rid": str(region[0])}).fetchall()
    
    print(f"\nAll districts:")
    for d in districts:
        print(f"  [{d[1]}] {d[0]} ({d[2] or 0} points)")
