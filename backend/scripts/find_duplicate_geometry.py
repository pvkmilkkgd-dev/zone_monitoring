"""Find districts with duplicate geometry."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Find districts with same geometry hash
    duplicates = conn.execute(text("""
        WITH geom_hashes AS (
            SELECT 
                d.id,
                d.name,
                r.name as region_name,
                MD5(ST_AsBinary(d.geom)::text) as geom_hash,
                ST_Area(d.geom::geography) / 1000000 as area_km2
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE d.geom IS NOT NULL
        )
        SELECT 
            geom_hash,
            COUNT(*) as cnt,
            STRING_AGG(name, ' | ' ORDER BY name) as names,
            MIN(region_name) as region,
            MIN(area_km2) as area
        FROM geom_hashes
        GROUP BY geom_hash
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)).fetchall()
    
    print(f"Found {len(duplicates)} groups with duplicate geometry:\n")
    
    total_dups = 0
    for d in duplicates:
        print(f"Hash: {d[0][:8]}... ({d[1]} districts, ~{d[4]:.0f} km2)")
        print(f"  Region: {d[3]}")
        print(f"  Names: {d[2][:200]}...")
        print()
        total_dups += d[1]
    
    print(f"\nTotal districts with duplicate geometry: {total_dups}")
    
    # Count unique geometries
    unique = conn.execute(text("""
        SELECT COUNT(DISTINCT MD5(ST_AsBinary(geom)::text)) as unique_geoms,
               COUNT(*) as total
        FROM districts
        WHERE geom IS NOT NULL
    """)).fetchone()
    
    print(f"Unique geometries: {unique[0]} out of {unique[1]} districts")
