"""
Скрипт для загрузки геометрии недостающих регионов из OSM.
"""
import sys
import json
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

DATA_DIR = Path(__file__).parent / "geodata"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# OSM relation IDs для недостающих регионов
# Используем ID украинских областей для территорий, так как они содержат корректную геометрию
MISSING_REGIONS = {
    "Донецкая Народная Республика": 71973,  # Donetsk Oblast
}


def get_region_geometry(osm_id: int, name: str):
    """Получить геометрию региона из Overpass API."""
    cache_file = DATA_DIR / f"osm_region_{osm_id}.json"
    
    if cache_file.exists():
        print(f"  [cache] {name}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    query = f"""
    [out:json][timeout:180];
    rel({osm_id});
    out geom;
    """
    
    print(f"  Загрузка {name} (OSM ID: {osm_id})...", end=" ", flush=True)
    
    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, timeout=300)
        response.raise_for_status()
        data = response.json()
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        print("OK")
        return data
    except Exception as e:
        print(f"ОШИБКА: {e}")
        return None


def osm_to_geojson(members: list) -> dict:
    """Конвертировать OSM members в GeoJSON."""
    outer_rings = []
    
    for member in members:
        if member.get('type') != 'way':
            continue
        
        geometry = member.get('geometry', [])
        if not geometry:
            continue
        
        coords = [[pt['lon'], pt['lat']] for pt in geometry]
        
        if member.get('role', 'outer') == 'outer':
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            if len(coords) >= 4:
                outer_rings.append([coords])
    
    if not outer_rings:
        return None
    
    if len(outer_rings) == 1:
        return {"type": "Polygon", "coordinates": outer_rings[0]}
    else:
        return {"type": "MultiPolygon", "coordinates": outer_rings}


def main():
    print("=" * 60)
    print("ЗАГРУЗКА ГЕОМЕТРИИ НЕДОСТАЮЩИХ РЕГИОНОВ")
    print("=" * 60)
    
    engine = create_engine(settings.DATABASE_URL)
    
    for name, osm_id in MISSING_REGIONS.items():
        data = get_region_geometry(osm_id, name)
        
        if not data or not data.get('elements'):
            print(f"  ! Нет данных для {name}")
            continue
        
        # Проверяем элементы
        relation = data['elements'][0]
        members = relation.get('members', [])
        
        geom = osm_to_geojson(members)
        
        if not geom:
            print(f"  ! Не удалось конвертировать геометрию для {name}")
            continue
        
        geom_json = json.dumps(geom, ensure_ascii=False)
        
        # Обновляем запись в БД
        with engine.connect() as conn:
            sql = text("""
                UPDATE regions SET
                    geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                    geom_simplified = ST_SimplifyPreserveTopology(
                        ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                        0.01
                    ),
                    bbox = ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                    updated_at = NOW()
                WHERE name = :name
            """)
            
            try:
                result = conn.execute(sql, {'geom': geom_json, 'name': name})
                conn.commit()
                if result.rowcount > 0:
                    print(f"  + {name} - геометрия обновлена")
                else:
                    print(f"  ! {name} - не найден в БД")
            except Exception as e:
                conn.rollback()
                print(f"  ! {name} - ошибка: {e}")
        
        # Пауза между запросами
        time.sleep(2)
    
    # Проверяем результат
    print("\n" + "=" * 60)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN geom IS NOT NULL THEN 1 ELSE 0 END) as with_geom
            FROM regions
        """)).fetchone()
        print(f"Всего регионов: {result[0]}")
        print(f"С геометрией: {result[1]}")
        print(f"Без геометрии: {result[0] - result[1]}")
    print("=" * 60)


if __name__ == "__main__":
    main()
