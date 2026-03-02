"""Load geometry for городской округ Троицк in Moscow via Nominatim."""
import sys, time, requests, json

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
TROITSK_ID = 'a695f381-da52-4256-be30-49dc5024b2da'

# Try known OSM relation IDs for Troitsk (Moscow)
# 1334914 - городской округ Троицк
# 13220604 - possible newer relation
candidates = [1334914, 13220604, 365437, 11493920, 365390]

for rel_id in candidates:
    time.sleep(1.5)
    url = f"https://nominatim.openstreetmap.org/lookup"
    params = {
        'osm_ids': f'R{rel_id}',
        'format': 'json',
        'polygon_geojson': 1,
        'accept-language': 'ru'
    }
    try:
        resp = requests.get(url, params=params,
                           headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=60)
        if resp.status_code != 200:
            print(f"  R{rel_id}: HTTP {resp.status_code}")
            continue
        results = resp.json()
        if not results:
            print(f"  R{rel_id}: no results")
            continue
        
        r = results[0]
        display = r.get('display_name', '')
        geojson = r.get('geojson', {})
        geom_type = geojson.get('type', 'none')
        print(f"  R{rel_id}: {display[:120]}")
        print(f"    geom_type={geom_type}")
        
        if geom_type in ('Polygon', 'MultiPolygon') and 'роиц' in display:
            print(f"    >>> MATCH! Saving geometry...")
            geojson_str = json.dumps(geojson)
            
            with ENGINE.begin() as c:
                c.execute(text("""
                    UPDATE districts 
                    SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)))
                    WHERE id = :id
                """), {'geojson': geojson_str, 'id': TROITSK_ID})
                
                row = c.execute(text("""
                    SELECT name, ST_NPoints(geom), ROUND(ST_Area(geom::geography)/1e6)
                    FROM districts WHERE id = :id
                """), {'id': TROITSK_ID}).fetchone()
                print(f"    Result: {row[0]}, pts={row[1]}, area={row[2]} km2")
            break
    except Exception as e:
        print(f"  R{rel_id}: error - {e}")
else:
    # Fallback: search Nominatim
    print("\n=== Searching Nominatim ===")
    time.sleep(1.5)
    params = {
        'q': 'Троицк Москва городской округ',
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 10,
        'accept-language': 'ru'
    }
    resp = requests.get("https://nominatim.openstreetmap.org/search", params=params,
                       headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=60)
    results = resp.json()
    print(f"  Found {len(results)} results")
    for r in results:
        osm_type = r.get('osm_type', '')
        osm_id = r.get('osm_id', '')
        display = r.get('display_name', '')[:120]
        geojson = r.get('geojson', {})
        geom_type = geojson.get('type', 'none')
        cls = r.get('class', '')
        typ = r.get('type', '')
        print(f"  {osm_type}/{osm_id} [{cls}/{typ}]: {display}")
        print(f"    geom={geom_type}")
        
        if geom_type in ('Polygon', 'MultiPolygon') and osm_type == 'relation':
            print(f"    >>> Saving...")
            geojson_str = json.dumps(geojson)
            with ENGINE.begin() as c:
                c.execute(text("""
                    UPDATE districts 
                    SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)))
                    WHERE id = :id
                """), {'geojson': geojson_str, 'id': TROITSK_ID})
                row = c.execute(text("""
                    SELECT name, ST_NPoints(geom), ROUND(ST_Area(geom::geography)/1e6)
                    FROM districts WHERE id = :id
                """), {'id': TROITSK_ID}).fetchone()
                print(f"    Result: {row[0]}, pts={row[1]}, area={row[2]} km2")
            break

print("\nDone!")
