"""
Импорт границ районов через Nominatim API (возвращает правильную геометрию)
"""
import json
import time
import urllib.request
import urllib.error
from sqlalchemy import text
from app.db.session import SessionLocal

# Список муниципальных образований Свердловской области (основные)
DISTRICTS = [
    "Алапаевский муниципальный округ",
    "Артемовский городской округ",
    "Артинский городской округ",
    "Асбестовский городской округ",
    "Байкаловский муниципальный округ",
    "Белоярский городской округ",
    "Березовский городской округ",
    "Бисертский городской округ",
    "Богдановичский городской округ",
    "Верхнесалдинский городской округ",
    "Верхнетуринский городской округ",
    "Волчанский городской округ",
    "Гаринский городской округ",
    "Горноуральский городской округ",
    "Дегтярск",
    "Екатеринбург",
    "Ирбитский муниципальный округ",
    "Каменский городской округ",
    "Камышловский городской округ",
    "Карпинский городской округ",
    "Качканарский городской округ",
    "Кировградский городской округ",
    "Краснотурьинск",
    "Красноуральский городской округ",
    "Кушвинский городской округ",
    "Невьянский городской округ",
    "Нижнесергинский муниципальный округ",
    "Нижнетуринский городской округ",
    "Нижний Тагил",
    "Нижняя Салда",
    "Новоуральский городской округ",
    "Первоуральск",
    "Полевской городской округ",
    "Пышминский городской округ",
    "Ревда",
    "Режевской городской округ",
    "Североуральский городской округ",
    "Серовский городской округ",
    "Сосьвинский городской округ",
    "Среднеуральск",
    "Сухой Лог",
    "Сысертский городской округ",
    "Тавдинский городской округ",
    "Талицкий городской округ",
    "Туринский городской округ",
]

def search_district_nominatim(district_name):
    """Ищет район через Nominatim API"""
    
    query = f"{district_name}, Свердловская область, Россия"
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&polygon_geojson=1&limit=1"
    
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Sverdlovsk-Districts-Import/1.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            results = json.loads(response.read().decode('utf-8'))
            
        if results and len(results) > 0:
            result = results[0]
            if 'geojson' in result:
                return {
                    "name": district_name,
                    "osm_id": result.get('osm_id'),
                    "osm_type": result.get('osm_type'),
                    "geometry": result['geojson']
                }
        return None
        
    except Exception as e:
        print(f"  [ERROR] {district_name}: {e}")
        return None


def import_to_database(districts_data, region_id):
    """Импортирует данные в базу"""
    
    db = SessionLocal()
    
    try:
        # Удаляем старые данные
        print("\nUdalenie staryh dannyh...")
        db.execute(text("DELETE FROM districts WHERE region_id = :region_id"), {"region_id": region_id})
        db.commit()
        
        print("Import novyh dannyh...")
        
        success_count = 0
        skip_count = 0
        
        for district in districts_data:
            try:
                geom_json = json.dumps(district['geometry'])
                
                # Конвертируем geometry в MultiPolygon, обрабатывая все типы
                query = text("""
                    INSERT INTO districts (id, region_id, name, osm_id, admin_level, geom)
                    VALUES (
                        uuid_generate_v4(),
                        :region_id,
                        :name,
                        :osm_id,
                        6,
                        CASE 
                            WHEN ST_GeometryType(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)) IN ('ST_Polygon')
                                THEN ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)))
                            WHEN ST_GeometryType(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)) IN ('ST_MultiPolygon')
                                THEN ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))
                            WHEN ST_GeometryType(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)) IN ('ST_Point')
                                THEN ST_Multi(ST_Buffer(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)::geography, 1000)::geometry)
                            WHEN ST_GeometryType(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)) IN ('ST_LineString')
                                THEN ST_Multi(ST_Buffer(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)::geography, 100)::geometry)
                            ELSE NULL
                        END
                    )
                """)
                
                db.execute(query, {
                    "region_id": region_id,
                    "name": district['name'],
                    "osm_id": district.get('osm_id'),
                    "geom": geom_json
                })
                db.commit()  # Commit после каждого района
                print(f"  [OK] {district['name']}")
                success_count += 1
                
            except Exception as e:
                db.rollback()  # Откатываем только текущую транзакцию
                print(f"  [SKIP] {district['name']}: {str(e)[:80]}")
                skip_count += 1
        
        print(f"\n[OK] Import zavershen! Uspeshno: {success_count}, Propusheno: {skip_count}")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


def main():
    print("=" * 70)
    print("Import granic rajonov cherez Nominatim API")
    print("=" * 70)
    print()
    
    # Получаем ID региона
    db = SessionLocal()
    result = db.execute(text("SELECT id FROM regions WHERE name LIKE '%Свердлов%'")).fetchone()
    db.close()
    
    if not result:
        print("[ERROR] Region ne najden")
        return
    
    region_id = result.id
    print(f"ID regiona: {region_id}")
    print()
    
    # Загружаем данные
    print(f"Zagruzka {len(DISTRICTS)} rajonov...")
    print("VNIMANIE: Nominatim trebuet 1 zapros v sekundu!")
    print()
    
    districts_data = []
    
    for i, district_name in enumerate(DISTRICTS, 1):
        print(f"[{i}/{len(DISTRICTS)}] {district_name}...")
        
        data = search_district_nominatim(district_name)
        if data:
            districts_data.append(data)
            print(f"  [OK]")
        else:
            print(f"  [SKIP] ne najdeno")
        
        # Ждем 1 секунду между запросами (требование Nominatim)
        if i < len(DISTRICTS):
            time.sleep(1.1)
    
    print()
    print(f"Zagruzheno: {len(districts_data)} iz {len(DISTRICTS)}")
    print()
    
    if districts_data:
        import_to_database(districts_data, region_id)
    else:
        print("[ERROR] Net dannyh dlya importa")


if __name__ == "__main__":
    main()
