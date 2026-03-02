"""Check what API would return for districts."""
import sys
import json
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

# Get Altai Krai region
with engine.connect() as conn:
    region = conn.execute(text("""
        SELECT id, name FROM regions WHERE name LIKE '%Алтайский%' LIMIT 1
    """)).fetchone()
    
    if not region:
        print("Region not found")
        sys.exit(1)
    
    print(f"Region: {region[1]}")
    region_id = str(region[0])
    
    # Same query as API
    result = conn.execute(text("""
        SELECT jsonb_build_object(
          'type','FeatureCollection',
          'features', COALESCE(jsonb_agg(
            jsonb_build_object(
              'type','Feature',
              'properties', jsonb_build_object(
                'id', id::text,
                'name', name
              ),
              'geometry', ST_AsGeoJSON(ST_ForceRHR(ST_MakeValid(geom)))::jsonb
            )
          ), '[]'::jsonb)
        ) AS fc
        FROM districts
        WHERE region_id = :region_id AND geom IS NOT NULL
    """), {"region_id": region_id}).scalar_one()
    
    features = result.get('features', [])
    print(f"Total features: {len(features)}")
    
    # Check a few features
    for f in features[:3]:
        name = f['properties']['name']
        geom = f['geometry']
        geom_type = geom['type'] if geom else None
        coords = geom.get('coordinates', []) if geom else []
        
        print(f"\n{name}:")
        print(f"  Type: {geom_type}")
        
        if geom_type == 'MultiPolygon':
            print(f"  Polygons: {len(coords)}")
            for i, poly in enumerate(coords[:2]):
                print(f"    Poly {i}: {len(poly)} rings")
                if poly and poly[0]:
                    ring = poly[0]
                    print(f"      Ring 0: {len(ring)} points")
                    print(f"      Sample coords: {ring[0]}, {ring[1] if len(ring)>1 else '...'}")
        elif geom_type == 'Polygon':
            print(f"  Rings: {len(coords)}")
            if coords and coords[0]:
                print(f"    Ring 0: {len(coords[0])} points")
                print(f"    Sample coords: {coords[0][0]}, {coords[0][1] if len(coords[0])>1 else '...'}")
    
    # Check overall bounds
    print("\n\nOverall bounds check:")
    bounds = conn.execute(text("""
        SELECT 
            MIN(ST_XMin(geom)) as min_lon,
            MAX(ST_XMax(geom)) as max_lon,
            MIN(ST_YMin(geom)) as min_lat,
            MAX(ST_YMax(geom)) as max_lat
        FROM districts
        WHERE region_id = :region_id AND geom IS NOT NULL
    """), {"region_id": region_id}).fetchone()
    
    print(f"  Lon: [{bounds[0]:.2f}, {bounds[1]:.2f}]")
    print(f"  Lat: [{bounds[2]:.2f}, {bounds[3]:.2f}]")
