"""
Fix Altai Krai cities:
1. Rename "город X" -> "городской округ X" 
2. Re-download geometry as городской округ (full municipal boundary, not city proper)
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

engine = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# Cities to fix: old name -> new name
CITIES = {
    "город Барнаул": "городской округ город Барнаул",
    "город Алейск": "городской округ город Алейск",
    "город Белокуриха": "городской округ город Белокуриха",
    "город Бийск": "городской округ город Бийск",
    "город Заринск": "городской округ город Заринск",
    "город Камень-на-Оби": "городской округ город Камень-на-Оби",
    "город Новоалтайск": "городской округ город Новоалтайск",
    "город Рубцовск": "городской округ город Рубцовск",
    "город Славгород": "городской округ город Славгород",
    "город Яровое": "городской округ город Яровое",
}


def search_overpass_relation(city_name, region="Алтайский край"):
    """Find the OSM relation ID for a городской округ."""
    # Try to find the relation via Overpass by name
    short_name = city_name.replace("городской округ город ", "").replace("городской округ ", "")
    
    queries_to_try = [
        # Search for городской округ relation within Altai Krai
        f"""
[out:json][timeout:30];
area["name"="{region}"]["admin_level"="4"]->.region;
relation["name"~"городской округ.*{short_name}|{short_name}"]["boundary"="administrative"]["admin_level"~"5|6"](area.region);
out tags;
""",
        f"""
[out:json][timeout:30];
area["name"="{region}"]["admin_level"="4"]->.region;
relation["name"~"{short_name}"]["boundary"="administrative"]["admin_level"="6"](area.region);
out tags;
""",
    ]
    
    for query in queries_to_try:
        try:
            resp = requests.post("https://overpass-api.de/api/interpreter",
                               data={'data': query}, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                for el in data.get('elements', []):
                    tags = el.get('tags', {})
                    name = tags.get('name', '')
                    if short_name.lower() in name.lower():
                        return el['id'], name
        except Exception as e:
            print(f"    Overpass error: {e}")
        time.sleep(2)
    
    return None, None


def download_polygon_by_id(osm_id):
    """Download polygon from Nominatim by OSM relation ID."""
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {'osm_ids': f'R{osm_id}', 'format': 'json', 'polygon_geojson': 1}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                geojson = data[0].get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    return geojson
    except:
        pass
    return None


def download_polygon_nominatim(query):
    """Download polygon from Nominatim search."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={'q': query, 'format': 'json', 'polygon_geojson': 1, 'limit': 5},
            headers=HEADERS, timeout=30
        )
        if resp.status_code == 200:
            for r in resp.json():
                geojson = r.get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    display = r.get('display_name', '')
                    if 'Алтайский' in display or 'Altai' in display:
                        return geojson
    except:
        pass
    return None


def main():
    # Get region ID
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM regions WHERE name = 'Алтайский край'")).fetchone()
        region_id = str(row[0])
    
    for old_name, new_name in CITIES.items():
        print(f"\n{old_name} -> {new_name}")
        
        # Find in DB
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT id FROM districts WHERE region_id = :rid AND name = :name"
            ), {"rid": region_id, "name": old_name}).fetchone()
        
        if not row:
            print(f"  Not found in DB, skipping")
            continue
        
        district_id = str(row[0])
        
        # Try to find via Overpass first (for exact OSM relation ID)
        short = old_name.replace("город ", "")
        osm_id, osm_name = search_overpass_relation(old_name)
        
        geojson = None
        if osm_id:
            print(f"  Found OSM relation: R{osm_id} ({osm_name})")
            geojson = download_polygon_by_id(osm_id)
            time.sleep(1.1)
        
        if not geojson:
            # Fallback: Nominatim search for городской округ
            for q in [
                f"городской округ {short}, Алтайский край, Россия",
                f"городской округ город {short}, Алтайский край",
                f"{short} городской округ, Алтайский край",
            ]:
                print(f"  Trying: {q}")
                geojson = download_polygon_nominatim(q)
                time.sleep(1.1)
                if geojson:
                    break
        
        if geojson:
            geojson_str = json.dumps(geojson)
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE districts SET 
                        name = :name,
                        geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                        geom_simplified = ST_SimplifyPreserveTopology(
                            ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005)
                    WHERE id = :id
                """), {"name": new_name, "geojson": geojson_str, "id": district_id})
                conn.commit()
            print(f"  OK (updated name + geometry)")
        else:
            # At least rename
            with engine.connect() as conn:
                conn.execute(text("UPDATE districts SET name = :name WHERE id = :id"),
                           {"name": new_name, "id": district_id})
                conn.commit()
            print(f"  Renamed only (no new geometry found)")
    
    # Also rename ЗАТО
    # ЗАТО stays as is
    
    # Final list of cities
    print(f"\n{'='*60}")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT name, 
                   ST_Area(geom::geography)/1000000 as area_km2
            FROM districts 
            WHERE region_id = :rid AND (name LIKE 'городской округ%' OR name LIKE 'ЗАТО%')
            ORDER BY name
        """), {"rid": region_id}).fetchall()
    
    print("Cities/ЗАТО:")
    for name, area in rows:
        print(f"  {name}: {area:.1f} km²")


if __name__ == "__main__":
    main()
