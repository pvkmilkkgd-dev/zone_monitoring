from app.db.session import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()

region_id = "6e9be0a9-07e4-4150-a0e6-befb15b09618"

# Получаем GeoJSON как его возвращает API
q = text("""
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
WHERE region_id = :region_id;
""")

result = db.execute(q, {"region_id": region_id}).scalar_one()
geojson = result if isinstance(result, dict) else json.loads(result)

print(f"Total features: {len(geojson['features'])}")
print()

# Проверяем каждый feature
for i, feature in enumerate(geojson['features'][:5], 1):
    props = feature['properties']
    geom = feature['geometry']
    
    print(f"Feature {i}: {props['name']}")
    print(f"  Type: {geom['type']}")
    
    if geom['type'] == 'MultiPolygon':
        coords = geom['coordinates']
        print(f"  Polygons: {len(coords)}")
        if len(coords) > 0:
            first_polygon = coords[0]
            print(f"  First polygon rings: {len(first_polygon)}")
            if len(first_polygon) > 0:
                first_ring = first_polygon[0]
                print(f"  First ring points: {len(first_ring)}")
                if len(first_ring) > 0:
                    print(f"  First point: {first_ring[0]}")
                    print(f"  Last point: {first_ring[-1]}")
    elif geom['type'] == 'Polygon':
        coords = geom['coordinates']
        print(f"  Rings: {len(coords)}")
        if len(coords) > 0:
            first_ring = coords[0]
            print(f"  First ring points: {len(first_ring)}")
            if len(first_ring) > 0:
                print(f"  First point: {first_ring[0]}")
    else:
        print(f"  Unknown type!")
    print()

db.close()
