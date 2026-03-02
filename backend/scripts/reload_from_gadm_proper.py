"""Reload district geometries from GADM with proper region matching."""
import sys
import json
import os
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from app.core.config import settings

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm_russia_level2.json'


def get_engine():
    return create_engine(settings.DATABASE_URL)


def download_gadm():
    """Download GADM Russia level 2 data."""
    os.makedirs(os.path.dirname(GADM_CACHE), exist_ok=True)
    
    if os.path.exists(GADM_CACHE):
        print("Loading cached GADM data...")
        with open(GADM_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    print("Downloading GADM Russia level 2...")
    url = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_RUS_2.json"
    
    resp = requests.get(url, timeout=300)
    if resp.status_code != 200:
        print(f"Failed to download GADM: {resp.status_code}")
        return None
    
    data = resp.json()
    
    with open(GADM_CACHE, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    
    print(f"Cached {len(data.get('features', []))} features")
    return data


def normalize_name(name):
    """Normalize name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    
    # Remove common suffixes
    suffixes = [
        'муниципальный район', 'городской округ', 'район', 'округ',
        'rayon', 'gorodskoy okrug', 'urban okrug', 'municipal district'
    ]
    for suffix in suffixes:
        name = name.replace(suffix, '')
    
    # Normalize characters
    name = name.replace('ё', 'е')
    name = name.replace('-', ' ').replace('—', ' ').replace('–', ' ')
    name = ' '.join(name.split())  # normalize whitespace
    
    return name.strip()


def normalize_region(name):
    """Normalize region name."""
    if not name:
        return ""
    name = name.lower().strip()
    
    suffixes = [
        'область', 'край', 'республика', 'автономный округ', 'автономная область',
        'oblast', 'kray', 'republic', 'autonomous'
    ]
    for suffix in suffixes:
        name = name.replace(suffix, '')
    
    name = name.replace('ё', 'е')
    name = name.replace('-', ' ').replace('—', ' ').replace('–', ' ')
    name = ' '.join(name.split())
    
    return name.strip()


def main():
    print("=" * 60)
    print("Перезагрузка геометрии районов из GADM")
    print("=" * 60)
    
    # Download GADM
    gadm = download_gadm()
    if not gadm:
        return
    
    features = gadm.get('features', [])
    print(f"GADM features: {len(features)}")
    
    # Build lookup: region_normalized -> [(district_normalized, feature), ...]
    gadm_by_region = {}
    for f in features:
        props = f.get('properties', {})
        region_en = props.get('NAME_1', '')
        region_ru = props.get('NL_NAME_1', '')
        district_en = props.get('NAME_2', '')
        district_ru = props.get('NL_NAME_2', '')
        
        # Use Russian names if available
        region_norm = normalize_region(region_ru) if region_ru else normalize_region(region_en)
        district_norm = normalize_name(district_ru) if district_ru else normalize_name(district_en)
        
        if region_norm and district_norm:
            if region_norm not in gadm_by_region:
                gadm_by_region[region_norm] = []
            gadm_by_region[region_norm].append((district_norm, district_ru or district_en, f))
    
    print(f"GADM regions: {len(gadm_by_region)}")
    
    # Get all districts from DB
    engine = get_engine()
    with engine.connect() as conn:
        districts = conn.execute(text("""
            SELECT d.id, d.name, r.name as region_name
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            ORDER BY r.name, d.name
        """)).fetchall()
    
    print(f"DB districts: {len(districts)}")
    
    # Match and update
    updated = 0
    not_found = []
    
    for d_id, d_name, r_name in districts:
        d_norm = normalize_name(d_name)
        r_norm = normalize_region(r_name)
        
        # Find in GADM by region
        gadm_districts = gadm_by_region.get(r_norm, [])
        
        matched = None
        for gd_norm, gd_name, gd_feature in gadm_districts:
            # Exact match
            if gd_norm == d_norm:
                matched = gd_feature
                break
            # Partial match (one contains the other)
            if d_norm in gd_norm or gd_norm in d_norm:
                matched = gd_feature
                break
            # First N chars match
            if len(d_norm) >= 4 and len(gd_norm) >= 4 and d_norm[:4] == gd_norm[:4]:
                matched = gd_feature
                break
        
        if matched:
            geom = matched.get('geometry')
            if geom:
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
                        """), {'geojson': geojson_str, 'id': str(d_id)})
                        conn.commit()
                    updated += 1
                except Exception as e:
                    not_found.append((r_name, d_name, f"DB error: {str(e)[:30]}"))
            else:
                not_found.append((r_name, d_name, "no geometry"))
        else:
            not_found.append((r_name, d_name, "not in GADM"))
    
    print(f"\n{'='*60}")
    print(f"Updated from GADM: {updated}")
    print(f"Not found: {len(not_found)}")
    print("=" * 60)
    
    if not_found:
        print(f"\nNot found ({len(not_found)}):")
        # Group by reason
        by_reason = {}
        for r, d, reason in not_found:
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(f"{r} -> {d}")
        
        for reason, items in by_reason.items():
            print(f"\n{reason} ({len(items)}):")
            for item in items[:10]:
                print(f"  {item}")
            if len(items) > 10:
                print(f"  ... and {len(items) - 10} more")


if __name__ == "__main__":
    main()
