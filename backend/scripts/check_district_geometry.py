"""Check district geometry quality."""
import sys
import json
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

# Get a sample district with geometry
with engine.connect() as conn:
    # Get first region
    region = conn.execute(text("""
        SELECT id, name FROM regions ORDER BY name LIMIT 1
    """)).fetchone()
    
    print(f"Region: {region[1]} (id: {region[0]})")
    
    # Get districts for this region
    districts = conn.execute(text("""
        SELECT d.id, d.name, 
               ST_GeometryType(d.geom) as geom_type,
               ST_NPoints(d.geom) as num_points,
               ST_IsValid(d.geom) as is_valid,
               ST_Area(d.geom::geography) / 1000000 as area_km2,
               ST_XMin(d.geom) as min_lon,
               ST_XMax(d.geom) as max_lon,
               ST_YMin(d.geom) as min_lat,
               ST_YMax(d.geom) as max_lat
        FROM districts d
        WHERE d.region_id = :region_id AND d.geom IS NOT NULL
        LIMIT 5
    """), {"region_id": str(region[0])}).fetchall()
    
    print(f"\nDistricts sample (first 5):")
    for d in districts:
        print(f"  {d[1]}:")
        print(f"    Type: {d[2]}, Points: {d[3]}, Valid: {d[4]}")
        print(f"    Area: {d[5]:.1f} km2")
        print(f"    Bounds: lon [{d[6]:.2f}, {d[7]:.2f}], lat [{d[8]:.2f}, {d[9]:.2f}]")
    
    # Get one full geometry as GeoJSON
    print("\n\nSample GeoJSON (first district):")
    sample = conn.execute(text("""
        SELECT d.name, ST_AsGeoJSON(d.geom)::json as geojson
        FROM districts d
        WHERE d.region_id = :region_id AND d.geom IS NOT NULL
        LIMIT 1
    """), {"region_id": str(region[0])}).fetchone()
    
    if sample:
        geojson = sample[1]
        print(f"  District: {sample[0]}")
        print(f"  Type: {geojson.get('type')}")
        coords = geojson.get('coordinates', [])
        if geojson.get('type') == 'MultiPolygon':
            print(f"  Polygons: {len(coords)}")
            for i, poly in enumerate(coords[:2]):
                print(f"    Polygon {i}: {len(poly)} rings")
                for j, ring in enumerate(poly[:1]):
                    print(f"      Ring {j}: {len(ring)} points")
                    if ring:
                        print(f"        First point: {ring[0]}")
                        print(f"        Last point: {ring[-1]}")
        elif geojson.get('type') == 'Polygon':
            print(f"  Rings: {len(coords)}")
            for i, ring in enumerate(coords[:1]):
                print(f"    Ring {i}: {len(ring)} points")
                if ring:
                    print(f"      First point: {ring[0]}")
                    print(f"      Last point: {ring[-1]}")
