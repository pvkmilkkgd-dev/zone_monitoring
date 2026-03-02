"""
Load districts geometry from GeoJSON file.

Usage:
    python scripts/load_geojson.py path/to/file.geojson "Название региона"
    
Example:
    python scripts/load_geojson.py C:\Downloads\altai.geojson "Алтайский край"
"""
import sys
import json

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings


def load_geojson(file_path, region_name):
    """Load GeoJSON file and update districts."""
    
    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    if not features:
        print("No features in file!")
        return
    
    print(f"Features in file: {len(features)}")
    
    # Show available properties
    sample = features[0].get('properties', {})
    print(f"Properties: {list(sample.keys())}")
    
    # Connect to DB
    engine = create_engine(settings.DATABASE_URL)
    
    # Get region ID
    with engine.connect() as conn:
        region = conn.execute(text(
            "SELECT id FROM regions WHERE name = :name"
        ), {"name": region_name}).fetchone()
        
        if not region:
            print(f"Region '{region_name}' not found!")
            return
        
        region_id = str(region[0])
        print(f"Region ID: {region_id}")
        
        # Get districts for this region
        districts = conn.execute(text("""
            SELECT id, name FROM districts WHERE region_id = :rid
        """), {"rid": region_id}).fetchall()
        
        print(f"Districts in DB: {len(districts)}")
    
    # Match and update
    updated = 0
    not_found = []
    
    for feat in features:
        props = feat.get('properties', {})
        geom = feat.get('geometry')
        
        if not geom:
            continue
        
        # Try common name fields
        name = (props.get('name') or props.get('NAME') or 
                props.get('name_ru') or props.get('NAME_2') or
                props.get('district') or props.get('raion') or '')
        
        if not name:
            continue
        
        # Find matching district
        matched = None
        name_lower = name.lower()
        
        for d_id, d_name in districts:
            d_lower = d_name.lower()
            # Exact or partial match
            if name_lower in d_lower or d_lower in name_lower:
                matched = d_id
                break
            # First word match
            if name_lower.split()[0] == d_lower.split()[0]:
                matched = d_id
                break
        
        if matched:
            geojson_str = json.dumps(geom)
            try:
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE districts
                        SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                            geom_simplified = ST_SimplifyPreserveTopology(
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                0.01
                            )
                        WHERE id = :id
                    """), {'geojson': geojson_str, 'id': str(matched)})
                    conn.commit()
                updated += 1
                print(f"  + {name}")
            except Exception as e:
                print(f"  ! {name}: {e}")
        else:
            not_found.append(name)
    
    print(f"\nUpdated: {updated}")
    print(f"Not matched: {len(not_found)}")
    
    if not_found:
        print("\nNot found in DB:")
        for n in not_found[:20]:
            print(f"  - {n}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    file_path = sys.argv[1]
    region_name = sys.argv[2]
    
    load_geojson(file_path, region_name)
