"""
Импорт реальных границ муниципальных районов Свердловской области
из OpenStreetMap через Overpass API
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from sqlalchemy import text
from app.db.session import SessionLocal

def download_districts_from_overpass():
    """Загружает границы районов Свердловской области через Overpass API"""
    
    # Overpass query для получения административных границ уровня 6 (муниципальные районы)
    # в Свердловской области
    # Используем out body/qt для получения полной геометрии
    query = """
    [out:json][timeout:90];
    area["name"="Свердловская область"]["admin_level"="4"]->.a;
    (
      relation["boundary"="administrative"]["admin_level"="6"](area.a);
    );
    out body;
    >;
    out skel qt;
    """
    
    # Используем альтернативный Overpass сервер
    overpass_url = "https://overpass.kumi.systems/api/interpreter"
    
    print("Отправка запроса в Overpass API...")
    print("Это может занять 30-60 секунд...")
    
    try:
        data = urllib.parse.urlencode({'data': query}).encode('utf-8')
        req = urllib.request.Request(overpass_url, data=data)
        req.add_header('User-Agent', 'Sverdlovsk-Districts-Import/1.0')
        
        with urllib.request.urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        print(f"Получено элементов: {len(result.get('elements', []))}")
        return result
        
    except urllib.error.URLError as e:
        print(f"Ошибка сети: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return None


def convert_osm_to_geojson(osm_data):
    """Конвертирует данные OSM в GeoJSON FeatureCollection"""
    
    features = []
    
    for element in osm_data.get('elements', []):
        if element.get('type') != 'relation':
            continue
            
        tags = element.get('tags', {})
        name = tags.get('name', tags.get('name:ru', 'Неизвестно'))
        
        # Собираем геометрию из members
        members = element.get('members', [])
        
        # Для отношений OSM геометрия уже включена в поле 'geometry' каждого member
        # Нужно собрать полигон из way members
        coordinates = []
        for member in members:
            if member.get('role') == 'outer' and member.get('type') == 'way':
                way_coords = []
                for node in member.get('geometry', []):
                    way_coords.append([node['lon'], node['lat']])
                if way_coords:
                    coordinates.append(way_coords)
        
        if not coordinates:
            print(f"  Пропуск {name}: нет геометрии")
            continue
        
        # Создаем MultiPolygon (так как могут быть несколько внешних колец)
        feature = {
            "type": "Feature",
            "properties": {
                "name": name,
                "osm_id": element.get('id'),
                "admin_level": tags.get('admin_level'),
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[coords] for coords in coordinates]  # Каждое кольцо - это полигон
            }
        }
        
        features.append(feature)
        print(f"  + {name}")
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


def import_to_database(geojson_data, region_id):
    """Импортирует GeoJSON данные в базу"""
    
    db = SessionLocal()
    
    try:
        # Сначала удаляем старые тестовые данные
        print("\nУдаление старых данных...")
        db.execute(text("DELETE FROM districts WHERE region_id = :region_id"), {"region_id": region_id})
        db.commit()
        
        print("Импорт новых данных...")
        for feature in geojson_data['features']:
            props = feature['properties']
            geom = feature['geometry']
            
            name = props['name']
            osm_id = props.get('osm_id')
            
            # Вставляем район
            # Используем ST_CollectionExtract для извлечения полигонов из GeometryCollection
            query = text("""
                INSERT INTO districts (id, region_id, name, osm_id, admin_level, geom)
                VALUES (
                    uuid_generate_v4(),
                    :region_id,
                    :name,
                    :osm_id,
                    :admin_level,
                    ST_Multi(ST_CollectionExtract(
                        ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                        3
                    ))
                )
            """)
            
            db.execute(query, {
                "region_id": region_id,
                "name": name,
                "osm_id": osm_id,
                "admin_level": 6,
                "geom": json.dumps(geom)
            })
            
            print(f"  [OK] {name}")
        
        db.commit()
        print("\n[OK] Import zavershon uspeshno!")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Oshibka pri importe: {e}")
        raise
    finally:
        db.close()


def main():
    print("=" * 60)
    print("Импорт границ муниципальных районов Свердловской области")
    print("=" * 60)
    print()
    
    # Получаем ID Свердловской области
    db = SessionLocal()
    result = db.execute(text("SELECT id FROM regions WHERE name LIKE '%Свердлов%'")).fetchone()
    db.close()
    
    if not result:
        print("[ERROR] Sverdlovskaya oblast ne najdena v BD")
        return
    
    region_id = result.id
    print(f"ID региона: {region_id}")
    print()
    
    # Загружаем данные из OSM
    osm_data = download_districts_from_overpass()
    if not osm_data:
        print("\n[ERROR] Ne udalos zagruzit dannye iz OpenStreetMap")
        return
    
    print()
    print("Конвертация в GeoJSON...")
    geojson_data = convert_osm_to_geojson(osm_data)
    
    if not geojson_data['features']:
        print("\n[ERROR] Ne najdeno ni odnogo rajona")
        return
    
    print(f"\nНайдено районов: {len(geojson_data['features'])}")
    print()
    
    # Импортируем в базу
    import_to_database(geojson_data, region_id)


if __name__ == "__main__":
    main()
