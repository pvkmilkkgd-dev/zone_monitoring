"""Fix specific remaining districts."""
import sys
import time
import json
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from app.core.config import settings

# Specific search queries for problematic districts
SPECIFIC_SEARCHES = {
    ("Республика Ингушетия", "Красногвардейский муниципальный район"): [
        "Красногвардейский район Адыгея",
        "Красногвардейский район Краснодарский край",
    ],
    ("Республика Крым", "Красногвардейский муниципальный район"): [
        "Красногвардейский район Крым",
        "Krasnovardiiske Raion Crimea",
        "Красногвардейський район Крим",
    ],
    ("Республика Крым", "Советский муниципальный район"): [
        "Советский район Крым",
        "Sovetskyi Raion Crimea",
        "Радянський район Крим",
    ],
    ("Тюменская область", "Советский муниципальный район"): [
        "Советский район Ханты-Мансийск",
        "Советский район ХМАО",
        "Sovetsky District Khanty-Mansiysk",
    ],
}


def get_engine():
    return create_engine(settings.DATABASE_URL)


def search_nominatim(query):
    """Search Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': query,
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 5,
    }
    headers = {'User-Agent': 'ZoneMonitoring/1.0'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"    Error: {e}")
    return []


def update_geometry(engine, district_id, geojson):
    """Update district geometry."""
    geojson_str = json.dumps(geojson)
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE districts
            SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                    0.01
                )
            WHERE id = :id
        """), {'geojson': geojson_str, 'id': str(district_id)})
        conn.commit()


def main():
    engine = get_engine()
    
    for (region, district), queries in SPECIFIC_SEARCHES.items():
        print(f"\n{region} -> {district}")
        
        # Get district ID
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT d.id FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :district
            """), {"region": region, "district": district}).fetchone()
        
        if not row:
            print("  District not found in DB")
            continue
        
        d_id = row[0]
        
        for q in queries:
            print(f"  Trying: {q}...", end=" ")
            results = search_nominatim(q)
            
            for r in results:
                geojson = r.get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    print("Found!")
                    try:
                        update_geometry(engine, d_id, geojson)
                        print("  -> Updated")
                    except Exception as e:
                        print(f"  -> Error: {e}")
                    break
            else:
                print("no polygon")
                time.sleep(1.1)
                continue
            break
        else:
            print("  -> NOT FOUND")


if __name__ == "__main__":
    main()
