"""Fix Kherson Oblast geometry with correct OSM ID."""
import sys
import json
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

CORRECT_OSM_ID = 71022  # Correct ID for Kherson Oblast

def main():
    print("=== Исправление Херсонской области ===")
    print(f"OSM ID: R{CORRECT_OSM_ID}")
    
    # Download from Nominatim
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        "osm_ids": f"R{CORRECT_OSM_ID}",
        "format": "geojson",
        "polygon_geojson": 1,
    }
    headers = {"User-Agent": "ZoneMonitoring/1.0"}
    
    print("Загрузка геометрии из Nominatim...", end=" ", flush=True)
    resp = requests.get(url, params=params, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    
    if not data.get("features"):
        print("Ошибка: нет данных")
        return
    
    print("OK")
    
    feature = data["features"][0]
    geometry = feature.get("geometry")
    
    if not geometry:
        print("Ошибка: нет геометрии")
        return
    
    geom_json = json.dumps(geometry, ensure_ascii=False)
    
    # Update in database
    print("Обновление в БД...", end=" ", flush=True)
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE regions SET
                geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                    0.01
                ),
                bbox = ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                updated_at = NOW()
            WHERE name = 'Херсонская область'
            RETURNING name, ROUND(ST_Area(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))::geography) / 1000000)
        """), {"geom": geom_json})
        conn.commit()
        
        row = result.fetchone()
        if row:
            print(f"OK - Площадь: {row[1]} км²")
        else:
            print("Ошибка: регион не найден")

if __name__ == "__main__":
    main()
