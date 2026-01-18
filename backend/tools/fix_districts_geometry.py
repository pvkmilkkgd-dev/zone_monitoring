"""
Исправление геометрии проблемных районов через Overpass API
Использует правильную сборку полигонов из ways
"""
from app.db.session import SessionLocal
from sqlalchemy import text
import json
import time
import urllib.request
import urllib.error
import urllib.parse

db = SessionLocal()

region_id = db.execute(
    text("SELECT id FROM regions WHERE name LIKE '%Свердлов%'")
).scalar()

# Находим проблемные районы (маленькие или с малым количеством точек)
problematic = db.execute(
    text("""
        SELECT 
            name,
            osm_id,
            ST_NPoints(geom) as num_points,
            ST_XMax(geom) - ST_XMin(geom) as width,
            ST_YMax(geom) - ST_YMin(geom) as height
        FROM districts
        WHERE region_id = :region_id
        AND (ST_NPoints(geom) < 50 OR 
             (ST_XMax(geom) - ST_XMin(geom)) < 0.01 OR
             (ST_YMax(geom) - ST_YMin(geom)) < 0.01)
        ORDER BY name
    """),
    {"region_id": region_id}
).fetchall()

print(f"Найдено проблемных районов: {len(problematic)}")
print()

def get_relation_full(osm_id):
    """Получает полную информацию о relation из Overpass API"""
    
    # Запрос для получения relation со всеми ways и nodes с геометрией
    query = f"""
    [out:json][timeout:60];
    (
      relation({osm_id});
    );
    (._;>;);
    out geom;
    """
    
    overpass_url = "https://overpass.kumi.systems/api/interpreter"
    
    try:
        data = urllib.parse.urlencode({'data': query}).encode('utf-8')
        req = urllib.request.Request(overpass_url, data=data)
        req.add_header('User-Agent', 'Sverdlovsk-Districts-Fix/1.0')
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        return result
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None

def connect_ways(ways_dict):
    """Соединяет ways в полигоны по общим узлам"""
    
    if not ways_dict:
        return []
    
    polygons = []
    used_ways = set()
    
    for start_way_id, start_way in ways_dict.items():
        if start_way_id in used_ways:
            continue
        
        # Начинаем новый полигон с этого way
        current_polygon = list(start_way)
        used_ways.add(start_way_id)
        
        # Ищем ways, которые можно присоединить
        changed = True
        while changed:
            changed = False
            
            # Ищем way, который начинается или заканчивается там же, где заканчивается текущий полигон
            last_point = current_polygon[-1]
            first_point = current_polygon[0]
            
            for way_id, way_coords in ways_dict.items():
                if way_id in used_ways:
                    continue
                
                way_start = way_coords[0]
                way_end = way_coords[-1]
                
                # Проверяем, можно ли присоединить way к концу полигона
                if abs(last_point[0] - way_start[0]) < 1e-6 and abs(last_point[1] - way_start[1]) < 1e-6:
                    # Присоединяем way к концу
                    current_polygon.extend(way_coords[1:])
                    used_ways.add(way_id)
                    changed = True
                    break
                elif abs(last_point[0] - way_end[0]) < 1e-6 and abs(last_point[1] - way_end[1]) < 1e-6:
                    # Присоединяем way в обратном порядке к концу
                    current_polygon.extend(reversed(way_coords[:-1]))
                    used_ways.add(way_id)
                    changed = True
                    break
                # Проверяем, можно ли присоединить way к началу полигона
                elif abs(first_point[0] - way_end[0]) < 1e-6 and abs(first_point[1] - way_end[1]) < 1e-6:
                    # Присоединяем way к началу
                    current_polygon = list(reversed(way_coords[:-1])) + current_polygon
                    used_ways.add(way_id)
                    changed = True
                    break
                elif abs(first_point[0] - way_start[0]) < 1e-6 and abs(first_point[1] - way_start[1]) < 1e-6:
                    # Присоединяем way в обратном порядке к началу
                    current_polygon = way_coords[1:] + current_polygon
                    used_ways.add(way_id)
                    changed = True
                    break
        
        # Замыкаем полигон если нужно
        if len(current_polygon) > 2:
            if current_polygon[0] != current_polygon[-1]:
                current_polygon.append(current_polygon[0])
            polygons.append(current_polygon)
    
    return polygons

def build_polygon_from_relation(osm_data, relation_id):
    """Собирает полигон из relation, правильно соединяя ways"""
    
    # Находим relation
    relation = None
    for elem in osm_data.get('elements', []):
        if elem.get('type') == 'relation' and elem.get('id') == relation_id:
            relation = elem
            break
    
    if not relation:
        print(f"    [DEBUG] Relation {relation_id} not found in response")
        return None
    
    # Собираем все ways с role='outer'
    outer_ways = {}
    members = relation.get('members', [])
    print(f"    [DEBUG] Relation has {len(members)} members")
    
    for member in members:
        if member.get('role') == 'outer' and member.get('type') == 'way':
            way_id = member.get('ref')
            # Ищем way в элементах
            found = False
            for elem in osm_data.get('elements', []):
                if elem.get('type') == 'way' and elem.get('id') == way_id:
                    if 'geometry' in elem:
                        coords = [[node['lon'], node['lat']] for node in elem.get('geometry', [])]
                        if len(coords) >= 2:
                            outer_ways[way_id] = coords
                            found = True
                    break
            
            if not found:
                print(f"    [DEBUG] Way {way_id} not found or has no geometry")
    
    print(f"    [DEBUG] Found {len(outer_ways)} outer ways with geometry")
    
    if not outer_ways:
        return None
    
    # Соединяем ways в полигоны
    polygons = connect_ways(outer_ways)
    
    if not polygons:
        print(f"    [DEBUG] Failed to connect ways into polygons")
        return None
    
    print(f"    [DEBUG] Created {len(polygons)} polygons")
    
    # Создаем MultiPolygon
    return {
        "type": "MultiPolygon",
        "coordinates": [[poly] for poly in polygons]
    }

fixed_count = 0
for district in problematic:
    print(f"Обработка: {district.name} (OSM ID: {district.osm_id})")
    print(f"  Текущее: {district.num_points} точек, размер {district.width:.6f}° x {district.height:.6f}°")
    
    if not district.osm_id:
        print(f"  [SKIP] Нет OSM ID")
        continue
    
    # Загружаем данные из Overpass
    osm_data = get_relation_full(district.osm_id)
    
    if not osm_data:
        print(f"  [SKIP] Не удалось загрузить")
        time.sleep(1)
        continue
    
    # Собираем геометрию
    geom_json = build_polygon_from_relation(osm_data, district.osm_id)
    
    if not geom_json:
        print(f"  [SKIP] Не удалось собрать геометрию")
        time.sleep(1)
        continue
    
    # Подсчитываем точки для проверки
    total_points = sum(len(poly[0]) for poly in geom_json['coordinates'])
    print(f"  Собрано: {total_points} точек")
    
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
                SELECT 
                    ST_NPoints(geom) as num_points,
                    ST_XMax(geom) - ST_XMin(geom) as width,
                    ST_YMax(geom) - ST_YMin(geom) as height
                FROM districts
                WHERE name = :name AND region_id = :region_id
            """),
            {"name": district.name, "region_id": region_id}
        ).fetchone()
        
        print(f"  [OK] Обновлено: {check.num_points} точек, размер {check.width:.6f}° x {check.height:.6f}°")
        fixed_count += 1
        
    except Exception as e:
        db.rollback()
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    time.sleep(1.5)  # Задержка между запросами

print()
print(f"Исправлено районов: {fixed_count} из {len(problematic)}")

db.close()
