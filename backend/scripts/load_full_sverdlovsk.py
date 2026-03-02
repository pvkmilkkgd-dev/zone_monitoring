"""Load ALL Sverdlovsk districts from GADM."""
import sys
import json
import os

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm_russia_level2.json'


def main():
    # Load GADM
    if not os.path.exists(GADM_CACHE):
        print("GADM cache not found! Run reload_from_gadm_proper.py first")
        return
    
    with open(GADM_CACHE, 'r', encoding='utf-8') as f:
        gadm = json.load(f)
    
    # Find Sverdlovsk features
    sverdlovsk_features = []
    for feat in gadm.get('features', []):
        props = feat.get('properties', {})
        region = props.get('NAME_1', '') or props.get('NL_NAME_1', '')
        if 'Sverdlovsk' in region or 'Свердлов' in region:
            sverdlovsk_features.append(feat)
    
    print(f"GADM Sverdlovsk districts: {len(sverdlovsk_features)}")
    
    if not sverdlovsk_features:
        print("No features found!")
        return
    
    # Show names
    print("\nGADM district names:")
    for f in sverdlovsk_features[:10]:
        props = f.get('properties', {})
        name_en = props.get('NAME_2', '')
        name_ru = props.get('NL_NAME_2', '')
        print(f"  {name_ru or name_en}")
    if len(sverdlovsk_features) > 10:
        print(f"  ... and {len(sverdlovsk_features) - 10} more")
    
    # Connect to DB
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Get region ID
        region = conn.execute(text(
            "SELECT id FROM regions WHERE name LIKE '%Свердлов%'"
        )).fetchone()
        
        if not region:
            print("Region not found in DB!")
            return
        
        region_id = str(region[0])
        print(f"\nRegion ID: {region_id}")
        
        # Get existing districts
        existing = conn.execute(text(
            "SELECT name FROM districts WHERE region_id = :rid"
        ), {"rid": region_id}).fetchall()
        existing_names = {e[0] for e in existing}
        print(f"Existing districts: {len(existing_names)}")
        
        # Add missing districts
        added = 0
        updated = 0
        
        for feat in sverdlovsk_features:
            props = feat.get('properties', {})
            geom = feat.get('geometry')
            
            name_ru = props.get('NL_NAME_2', '')
            name_en = props.get('NAME_2', '')
            name = name_ru if name_ru else name_en
            
            if not name or not geom:
                continue
            
            # Format name
            if 'район' not in name.lower() and 'округ' not in name.lower():
                name = f"{name} муниципальный район"
            
            geojson_str = json.dumps(geom)
            
            # Check if exists
            match = None
            for ex_name in existing_names:
                if name.lower() in ex_name.lower() or ex_name.lower() in name.lower():
                    match = ex_name
                    break
            
            if match:
                # Update existing
                conn.execute(text("""
                    UPDATE districts
                    SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                        geom_simplified = ST_SimplifyPreserveTopology(
                            ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.01)
                    WHERE region_id = :rid AND name = :name
                """), {'geojson': geojson_str, 'rid': region_id, 'name': match})
                updated += 1
            else:
                # Insert new
                from uuid import uuid4
                conn.execute(text("""
                    INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                    VALUES (:id, :rid, :name, 
                            ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                            ST_SimplifyPreserveTopology(
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.01),
                            NOW())
                """), {'id': str(uuid4()), 'rid': region_id, 'name': name, 'geojson': geojson_str})
                added += 1
                print(f"  + {name}")
        
        conn.commit()
        
        print(f"\nAdded: {added}")
        print(f"Updated: {updated}")
        
        # Final count
        final = conn.execute(text(
            "SELECT COUNT(*) FROM districts WHERE region_id = :rid"
        ), {"rid": region_id}).scalar()
        print(f"Total now: {final}")


if __name__ == "__main__":
    main()
