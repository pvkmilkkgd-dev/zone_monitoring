"""
Download geometry for districts from OSM/GADM.

This script downloads district geometries from:
1. GADM Level 2 (municipal districts)
2. OSM Overpass API (as fallback)

Usage:
    python download_districts_geometry.py --region "Алтайский край"  # One region
    python download_districts_geometry.py --all                       # All regions
    python download_districts_geometry.py --status                    # Show status
"""
import argparse
import json
import sys
import time
import zipfile
from io import BytesIO
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

CACHE_DIR = Path(__file__).parent / "geodata" / "districts_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_RUS_2.json.zip"


def get_engine():
    return create_engine(settings.DATABASE_URL)


def show_status():
    """Show current status of districts geometry."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Overall stats
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN d.geom IS NOT NULL THEN 1 ELSE 0 END) as with_geom
            FROM districts d
        """)).fetchone()
        
        print(f"Всего районов: {result[0]}")
        print(f"С геометрией: {result[1]}")
        print(f"Без геометрии: {result[0] - result[1]}")
        
        # By region
        print("\nПо регионам (без геометрии):")
        result = conn.execute(text("""
            SELECT r.name, COUNT(d.id) as total,
                   SUM(CASE WHEN d.geom IS NOT NULL THEN 1 ELSE 0 END) as with_geom
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            GROUP BY r.name
            HAVING SUM(CASE WHEN d.geom IS NULL THEN 1 ELSE 0 END) > 0
            ORDER BY r.name
        """)).fetchall()
        
        for row in result:
            missing = row[1] - row[2]
            print(f"  {row[0]}: {missing}/{row[1]} без геометрии")


def download_gadm_level2():
    """Download and cache GADM Level 2 data for Russia."""
    cache_file = CACHE_DIR / "gadm_rus_level2.json"
    
    if cache_file.exists():
        print("Загрузка GADM из кэша...")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    print("Скачивание GADM Level 2 для России...")
    print(f"URL: {GADM_URL}")
    
    try:
        resp = requests.get(GADM_URL, timeout=300, stream=True)
        resp.raise_for_status()
        
        # Extract JSON from ZIP
        with zipfile.ZipFile(BytesIO(resp.content)) as zf:
            json_name = [n for n in zf.namelist() if n.endswith('.json')][0]
            with zf.open(json_name) as f:
                data = json.load(f)
        
        # Cache it
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        print(f"Скачано {len(data.get('features', []))} районов")
        return data
    
    except Exception as e:
        print(f"Ошибка скачивания GADM: {e}")
        return None


def normalize_name(name):
    """Normalize district name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in ['муниципальный район', 'городской округ', 'район', 'округ', 'край', 'область', 
                   'республика', 'автономный', 'rayon', 'gorsovet']:
        name = name.replace(suffix, '')
    # Normalize whitespace and dashes
    name = ' '.join(name.split())
    name = name.replace('ё', 'е')
    name = name.replace('-', ' ').replace('—', ' ').replace('–', ' ')
    # Remove parentheses and their content
    import re
    name = re.sub(r'\([^)]*\)', '', name)
    return name.strip()


def normalize_gadm_name(name):
    """Normalize GADM name - they often have no spaces."""
    if not name:
        return ""
    name = name.lower().strip()
    
    # GADM often concatenates words, try to split common patterns
    # e.g., "Алтайскийкрай" -> "алтайский"
    # e.g., "Алейскийрайон" -> "алейский"
    
    # Remove common suffixes first
    for suffix in ['район', 'край', 'область', 'республика', 'округ', 'rayon', 'kray', 'oblast']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    # Also handle concatenated forms
    for suffix in ['ский', 'ская', 'ское', 'ий', 'ая', 'ое']:
        if name.endswith(suffix + 'район') or name.endswith(suffix + 'край'):
            idx = name.rfind(suffix) + len(suffix)
            name = name[:idx]
            break
    
    name = name.replace('ё', 'е')
    name = name.replace('-', ' ').replace('—', ' ').replace('–', ' ')
    
    # Remove parentheses content like "(горсовет)"
    import re
    name = re.sub(r'\([^)]*\)', '', name)
    
    return name.strip()


def load_districts_from_gadm(region_name=None):
    """Load district geometries from GADM."""
    engine = get_engine()
    
    # Download GADM data
    gadm = download_gadm_level2()
    if not gadm:
        return
    
    # Build lookup by region and district name
    # Use multiple keys for better matching
    gadm_lookup = {}
    for feature in gadm.get('features', []):
        props = feature.get('properties', {})
        region_en = props.get('NAME_1', '')
        region_ru = props.get('NL_NAME_1', '')
        district_en = props.get('NAME_2', '')
        district_ru = props.get('NL_NAME_2', '')
        
        if region_en and district_en:
            # English name key
            key1 = (normalize_gadm_name(region_en), normalize_gadm_name(district_en))
            gadm_lookup[key1] = feature
            
            # Russian name key
            if region_ru and district_ru:
                key2 = (normalize_gadm_name(region_ru), normalize_gadm_name(district_ru))
                gadm_lookup[key2] = feature
    
    print(f"GADM: {len(gadm_lookup)} записей в lookup")
    
    # Get districts from DB
    with engine.connect() as conn:
        if region_name:
            result = conn.execute(text("""
                SELECT d.id, d.name, r.name as region_name
                FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region_name AND d.geom IS NULL
            """), {"region_name": region_name}).fetchall()
        else:
            result = conn.execute(text("""
                SELECT d.id, d.name, r.name as region_name
                FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE d.geom IS NULL
            """)).fetchall()
        
        districts = list(result)
    
    print(f"Районов без геометрии: {len(districts)}")
    
    # Match and update
    matched = 0
    not_matched = []
    
    for district_id, district_name, reg_name in districts:
        norm_db_region = normalize_name(reg_name)
        norm_db_district = normalize_name(district_name)
        
        # Try exact match first
        key = (norm_db_region, norm_db_district)
        feature = gadm_lookup.get(key)
        
        # Try with GADM normalization
        if not feature:
            key = (normalize_gadm_name(reg_name), normalize_gadm_name(district_name))
            feature = gadm_lookup.get(key)
        
        # Try partial match on district name
        if not feature:
            for (r, d), f in gadm_lookup.items():
                # Check if region matches (within 3 char difference)
                if norm_db_region in r or r in norm_db_region or abs(len(norm_db_region) - len(r)) < 5:
                    # Check if district matches
                    if norm_db_district in d or d in norm_db_district:
                        feature = f
                        break
                    # Check first 5 characters
                    if len(d) >= 5 and len(norm_db_district) >= 5:
                        if d[:5] == norm_db_district[:5]:
                            feature = f
                            break
        
        if feature:
            geometry = feature.get('geometry')
            if geometry:
                geom_json = json.dumps(geometry, ensure_ascii=False)
                
                with engine.connect() as conn:
                    try:
                        conn.execute(text("""
                            UPDATE districts SET
                                geom = ST_Multi(ST_CollectionExtract(
                                    ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                                geom_simplified = ST_SimplifyPreserveTopology(
                                    ST_Multi(ST_CollectionExtract(
                                        ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                                    0.001
                                ),
                                name_ru = :name_ru
                            WHERE id = :id
                        """), {
                            "geom": geom_json,
                            "id": district_id,
                            "name_ru": feature.get('properties', {}).get('NL_NAME_2', '')
                        })
                        conn.commit()
                        matched += 1
                        print(f"  + {region_name} -> {district_name}")
                    except Exception as e:
                        conn.rollback()
                        print(f"  ! {district_name}: {e}")
        else:
            not_matched.append((reg_name, district_name))
    
    print(f"\nОбновлено: {matched}/{len(districts)}")
    
    if not_matched and len(not_matched) <= 50:
        print(f"\nНе найдено ({len(not_matched)}):")
        for reg, dist in not_matched[:30]:
            print(f"  {reg} -> {dist}")


def main():
    parser = argparse.ArgumentParser(description="Download district geometries")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--region", help="Load for specific region")
    parser.add_argument("--all", action="store_true", help="Load for all regions")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.region:
        load_districts_from_gadm(args.region)
        show_status()
    elif args.all:
        load_districts_from_gadm()
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
