"""
Исправление районов с неправильной геометрией (точки/линии вместо полигонов)
"""
from app.db.session import SessionLocal
from sqlalchemy import text
import json
import time
import urllib.request
import urllib.error
import urllib.parse

db = SessionLocal()

# Находим проблемные районы (мало точек или очень маленький размер)
problematic = db.execute(
    text("""
        SELECT 
            name,
            osm_id,
            ST_NPoints(geom) as num_points,
            ST_XMax(geom) - ST_XMin(geom) as width,
            ST_YMax(geom) - ST_YMin(geom) as height
        FROM districts
        WHERE region_id = (SELECT id FROM regions WHERE name LIKE '%Свердлов%')
        AND (ST_NPoints(geom) < 50 OR 
             (ST_XMax(geom) - ST_XMin(geom)) < 0.05 OR
             (ST_YMax(geom) - ST_YMin(geom)) < 0.05)
        ORDER BY ST_NPoints(geom) ASC
    """)
).fetchall()

print(f"Найдено проблемных районов: {len(problematic)}")
print()

region_id = db.execute(
    text("SELECT id FROM regions WHERE name LIKE '%Свердлов%'")
).scalar()

def search_district_overpass(district_name, osm_id=None):
    """Ищет район через Overpass API по имени или OSM ID"""
    
    if osm_id:
        # Используем OSM ID для точного поиска
        query = f"""
        [out:json][timeout:30];
        (
          relation({osm_id});
        );
        out body;
        >;
        out skel qt;
        """
    else:
        # Ищем по имени
        query = f"""
        [out:json][timeout:30];
        (
          relation["boundary"="administrative"]["admin_level"="6"]["name"="{district_name}"](area["name"="Свердловская область"]["admin_level"="4"]);
        );
        out body;
        >;
        out skel qt;
        """
    
    overpass_url = "https://overpass.kumi.systems/api/interpreter"
    
    try:
        data = urllib.parse.urlencode({'data': query}).encode('utf-8')
        req = urllib.request.Request(overpass_url, data=data)
        req.add_header('User-Agent', 'Sverdlovsk-Districts-Fix/1.0')
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        return result
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None

def convert_relation_to_geojson(osm_data, district_name):
    """Конвертирует OSM relation в GeoJSON"""
    
    for element in osm_data.get('elements', []):
        if element.get('type') != 'relation':
            continue
            
        tags = element.get('tags', {})
        name = tags.get('name', tags.get('name:ru', district_name))
        
        # Собираем геометрию из members
        members = element.get('members', [])
        
        # Нужно собрать все ways с role='outer' в полигоны
        outer_ways = []
        for member in members:
            if member.get('role') == 'outer' and member.get('type') == 'way':
                way_id = member.get('ref')
                # Ищем way в элементах
                for elem in osm_data.get('elements', []):
                    if elem.get('type') == 'way' and elem.get('id') == way_id:
                        if 'geometry' in elem:
                            coords = [[node['lon'], node['lat']] for node in elem.get('geometry', [])]
                            if coords:
                                outer_ways.append(coords)
                        break
        
        if not outer_ways:
            return None
        
        # Создаем MultiPolygon из всех outer ways
        return {
            "type": "MultiPolygon",
            "coordinates": [[way] for way in outer_ways]
        }
    
    return None

# Исправляем проблемные районы
fixed_count = 0
for district in problematic:
    print(f"Исправление: {district.name} (OSM ID: {district.osm_id})")
    print(f"  Текущее: {district.num_points} точек, размер {district.width:.6f}° x {district.height:.6f}°")
    
    # Загружаем данные из Overpass
    osm_data = search_district_overpass(district.name, district.osm_id)
    
    if not osm_data:
        print(f"  [SKIP] Не удалось загрузить из Overpass")
        time.sleep(1)
        continue
    
    # Конвертируем в GeoJSON
    geom_json = convert_relation_to_geojson(osm_data, district.name)
    
    if not geom_json:
        print(f"  [SKIP] Не удалось собрать геометрию")
        time.sleep(1)
        continue
    
    # Обновляем в базе
    try:
        query = text("""
            UPDATE districts
            SET geom = ST_Multi(ST_CollectionExtract(
                ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                3
            ))
            WHERE name = :name AND region_id = :region_id
        """)
        
        db.execute(query, {
            "name": district.name,
            "region_id": region_id,
            "geom": json.dumps(geom_json)
        })
        db.commit()
        
        # Проверяем результат
        check = db.execute(
            text("""
                SELECT ST_NPoints(geom) as num_points
                FROM districts
                WHERE name = :name AND region_id = :region_id
            """),
            {"name": district.name, "region_id": region_id}
        ).fetchone()
        
        print(f"  [OK] Обновлено: {check.num_points} точек")
        fixed_count += 1
        
    except Exception as e:
        db.rollback()
        print(f"  [ERROR] {e}")
    
    time.sleep(1)  # Задержка между запросами

print()
print(f"Исправлено районов: {fixed_count} из {len(problematic)}")

db.close()
