"""
Retry loading districts for regions that failed in the first pass.
Uses different Overpass servers and longer timeouts.
Also handles regions where OSM uses different admin_level.
"""
import sys
import os
import json
import time
import requests
from uuid import uuid4

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

# Special region name mappings for OSM search
REGION_OSM_CONFIG = {
    # New territories - may not have standard boundaries in OSM
    "Донецкая Народная Республика": {
        "osm_name": "Донецкая область",
        "admin_levels": "4|5|6|7|8",
    },
    "Луганская Народная Республика": {
        "osm_name": "Луганская область", 
        "admin_levels": "4|5|6|7|8",
    },
    "Запорожская область": {
        "osm_name": "Запорожская область",
        "admin_levels": "4|5|6|7|8",
    },
    "Херсонская область": {
        "osm_name": "Херсонская область",
        "admin_levels": "4|5|6|7|8",
    },
    # Republics often have different admin structure
    "Республика Адыгея": {
        "osm_name": "Адыгея",
        "admin_levels": "5|6|7",
    },
    "Кабардино-Балкарская Республика": {
        "osm_name": "Кабардино-Балкарская Республика",
        "admin_levels": "5|6|7",
    },
    "Карачаево-Черкесская Республика": {
        "osm_name": "Карачаево-Черкесская Республика",
        "admin_levels": "5|6|7",
    },
    "Республика Алтай": {
        "osm_name": "Республика Алтай",
        "admin_levels": "5|6|7",
    },
    "Республика Башкортостан": {
        "osm_name": "Башкортостан",
        "admin_levels": "5|6|7",
    },
    "Республика Дагестан": {
        "osm_name": "Дагестан",
        "admin_levels": "5|6|7",
    },
    "Республика Ингушетия": {
        "osm_name": "Ингушетия",
        "admin_levels": "5|6|7",
    },
    "Республика Калмыкия": {
        "osm_name": "Калмыкия",
        "admin_levels": "5|6|7",
    },
    "Республика Карелия": {
        "osm_name": "Карелия",
        "admin_levels": "5|6|7",
    },
    "Республика Коми": {
        "osm_name": "Коми",
        "admin_levels": "5|6|7",
    },
    "Республика Крым": {
        "osm_name": "Крым",
        "admin_levels": "5|6|7",
    },
    "Республика Марий Эл": {
        "osm_name": "Марий Эл",
        "admin_levels": "5|6|7",
    },
    "Республика Мордовия": {
        "osm_name": "Мордовия",
        "admin_levels": "5|6|7",
    },
    "Республика Саха (Якутия)": {
        "osm_name": "Саха (Якутия)",
        "admin_levels": "5|6|7",
    },
    "Республика Северная Осетия - Алания": {
        "osm_name": "Северная Осетия — Алания",
        "admin_levels": "5|6|7",
    },
    "Республика Татарстан": {
        "osm_name": "Татарстан",
        "admin_levels": "5|6|7",
    },
    "Удмуртская Республика": {
        "osm_name": "Удмуртия",
        "admin_levels": "5|6|7",
    },
    "Чеченская Республика": {
        "osm_name": "Чечня",
        "admin_levels": "5|6|7",
    },
    "Чувашская Республика": {
        "osm_name": "Чувашия",
        "admin_levels": "5|6|7",
    },
    # Standard oblasts that had Overpass timeout  
    "Воронежская область": {"osm_name": "Воронежская область", "admin_levels": "6"},
    "Московская область": {"osm_name": "Московская область", "admin_levels": "6"},
    "Мурманская область": {"osm_name": "Мурманская область", "admin_levels": "6"},
    "Ненецкий автономный округ": {"osm_name": "Ненецкий автономный округ", "admin_levels": "6"},
    "Псковская область": {"osm_name": "Псковская область", "admin_levels": "6"},
    "Рязанская область": {"osm_name": "Рязанская область", "admin_levels": "6"},
    "Сахалинская область": {"osm_name": "Сахалинская область", "admin_levels": "6"},
    "Смоленская область": {"osm_name": "Смоленская область", "admin_levels": "6"},
    "Томская область": {"osm_name": "Томская область", "admin_levels": "6"},
    "Ханты-Мансийский автономный округ - Югра": {
        "osm_name": "Ханты-Мансийский автономный округ — Югра",
        "admin_levels": "5|6|7",
    },
}

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

def get_osm_relations(region_name, server_idx=0):
    """Get admin_level relations within a region from Overpass."""
    config = REGION_OSM_CONFIG.get(region_name, {
        "osm_name": region_name,
        "admin_levels": "6",
    })
    osm_name = config["osm_name"]
    admin_levels = config["admin_levels"]
    
    # Try finding region by different admin_levels (2, 3, 4)
    for region_al in ["4", "3", "2"]:
        query = f"""
[out:json][timeout:120];
area["name"="{osm_name}"]["admin_level"="{region_al}"]->.region;
relation["boundary"="administrative"]["admin_level"~"^({admin_levels})$"](area.region);
out tags;
"""
        server = OVERPASS_SERVERS[server_idx % len(OVERPASS_SERVERS)]
        
        try:
            resp = requests.post(server, data={'data': query}, timeout=150)
            if resp.status_code != 200:
                continue
            
            data = resp.json()
            elements = data.get('elements', [])
            
            result = []
            for el in elements:
                tags = el.get('tags', {})
                name = tags.get('name', '')
                osm_id = el.get('id')
                if name and osm_id:
                    result.append({'osm_id': osm_id, 'name': name})
            
            if result:
                return result
                
        except Exception as e:
            print(f"    Overpass error (server {server_idx}, level {region_al}): {e}")
    
    return None


def download_polygon(osm_id):
    """Download polygon from Nominatim by OSM relation ID."""
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        'osm_ids': f'R{osm_id}',
        'format': 'json',
        'polygon_geojson': 1,
    }
    headers = {'User-Agent': 'ZoneMonitoring/1.0'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                geojson = data[0].get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    return geojson
    except Exception as e:
        pass
    
    return None


def insert_district(region_id, name, geojson):
    """Insert district into DB."""
    geojson_str = json.dumps(geojson)
    
    with ENGINE.connect() as conn:
        conn.execute(text("""
            INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
            VALUES (:id, :rid, :name,
                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                    ST_SimplifyPreserveTopology(
                        ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                    NOW())
        """), {
            'id': str(uuid4()),
            'rid': region_id,
            'name': name,
            'geojson': geojson_str,
        })
        conn.commit()


def clear_districts(region_id):
    """Clear existing districts for region."""
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
        conn.commit()


def get_regions_needing_reload():
    """Get regions with 0 districts or that are in the failed list."""
    with ENGINE.connect() as conn:
        rows = conn.execute(text("""
            SELECT r.id, r.name, COUNT(d.id) as cnt
            FROM regions r
            LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.id, r.name
            HAVING COUNT(d.id) = 0
            ORDER BY r.name
        """)).fetchall()
    return [(str(r[0]), r[1], r[2]) for r in rows]


def main():
    # Get regions with 0 districts
    zero_regions = get_regions_needing_reload()
    print(f"Regions with 0 districts: {len(zero_regions)}")
    for _, name, cnt in zero_regions:
        print(f"  {name}: {cnt}")
    
    print(f"\nProcessing {len(zero_regions)} regions...\n")
    
    total_inserted = 0
    still_failed = []
    
    for i, (region_id, region_name, _) in enumerate(zero_regions):
        print(f"\n[{i+1}/{len(zero_regions)}] {region_name}")
        
        # Try each Overpass server
        relations = None
        for server_idx in range(len(OVERPASS_SERVERS)):
            relations = get_osm_relations(region_name, server_idx)
            if relations:
                break
            time.sleep(5)
        
        if not relations:
            print(f"    STILL FAILED - no relations found")
            still_failed.append(region_name)
            time.sleep(3)
            continue
        
        print(f"    Found {len(relations)} districts")
        
        # Clear and reload
        clear_districts(region_id)
        
        inserted = 0
        for rel in relations:
            geojson = download_polygon(rel['osm_id'])
            if geojson:
                try:
                    insert_district(region_id, rel['name'], geojson)
                    inserted += 1
                except Exception as e:
                    print(f"    Insert error for {rel['name']}: {e}")
            time.sleep(1.1)
        
        print(f"    OK: {inserted}/{len(relations)}")
        total_inserted += inserted
        time.sleep(3)
    
    print(f"\n{'='*60}")
    print(f"Total districts loaded: {total_inserted}")
    
    if still_failed:
        print(f"\nStill failed ({len(still_failed)}):")
        for name in still_failed:
            print(f"  - {name}")
    
    # Final stats
    with ENGINE.connect() as conn:
        stats = conn.execute(text("""
            SELECT r.name, COUNT(d.id) as cnt
            FROM regions r
            LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.name
            ORDER BY cnt, r.name
        """)).fetchall()
    
    print(f"\nAll regions:")
    for name, cnt in stats:
        print(f"  {cnt:4d}  {name}")


if __name__ == "__main__":
    main()
