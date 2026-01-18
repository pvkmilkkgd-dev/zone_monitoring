"""
Перезагрузка районов с неправильной геометрией из Overpass API
"""
from app.db.session import SessionLocal
from sqlalchemy import text
import json
import time
import urllib.request
import urllib.error
import urllib.parse

try:
    import osmtogeojson
    HAS_OSMTOGEOJSON = True
except ImportError:
    HAS_OSMTOGEOJSON = False
    print("WARNING: osmtogeojson not available, using manual conversion")

db = SessionLocal()

region_id = db.execute(
    text("SELECT id FROM regions WHERE name LIKE '%Свердлов%'")
).scalar()

# Находим проблемные районы
problematic = db.execute(
    text("""
        SELECT 
            name,
            osm_id
        FROM districts
        WHERE region_id = :region_id
        AND (ST_NPoints(geom) < 50 OR 
             (ST_XMax(geom) - ST_XMin(geom)) < 0.05 OR
             (ST_YMax(geom) - ST_YMin(geom)) < 0.05)
        ORDER BY name
    """),
    {"region_id": region_id}
).fetchall()

print(f"Найдено проблемных районов: {len(problematic)}")
print()

def get_relation_geojson(osm_id):
    """Получает GeoJSON для relation через Overpass API"""
    
    # Запрос для получения relation с полной геометрией
    # Используем out geom для получения уже собранной геометрии
    query = f"""
    [out:json][timeout:30];
    (
      relation({osm_id});
    );
    out geom;
    """
    
    overpass_url = "https://overpass.kumi.systems/api/interpreter"
    
    try:
        data = urllib.parse.urlencode({'data': query}).encode('utf-8')
        req = urllib.request.Request(overpass_url, data=data)
        req.add_header('User-Agent', 'Sverdlovsk-Districts-Reload/1.0')
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        return result
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None

def build_polygon_from_ways(osm_data, relation_id):
    """Собирает полигон из ways relation"""
    
    # Находим relation
    relation = None
    for elem in osm_data.get('elements', []):
        if elem.get('type') == 'relation' and elem.get('id') == relation_id:
            relation = elem
            break
    
    if not relation:
        return None
    
    # С out geom геометрия уже собрана в members
    # Собираем все outer rings
    outer_rings = []
    for member in relation.get('members', []):
        if member.get('role') == 'outer':
            if member.get('type') == 'way' and 'geometry' in member:
                # Way с геометрией
                coords = [[node['lon'], node['lat']] for node in member.get('geometry', [])]
                if len(coords) > 2:
                    # Замыкаем кольцо если нужно
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    outer_rings.append(coords)
            elif member.get('type') == 'relation':
                # Вложенная relation - пропускаем для простоты
                pass
    
    if not outer_rings:
        return None
    
    # Создаем MultiPolygon из всех outer rings
    return {
        "type": "MultiPolygon",
        "coordinates": [[ring] for ring in outer_rings]
    }

fixed_count = 0
for district in problematic:
    print(f"Обработка: {district.name} (OSM ID: {district.osm_id})")
    
    if not district.osm_id:
        print(f"  [SKIP] Нет OSM ID")
        continue
    
    # Загружаем данные из Overpass
    osm_data = get_relation_geojson(district.osm_id)
    
    if not osm_data:
        print(f"  [SKIP] Не удалось загрузить")
        time.sleep(1)
        continue
    
    # Собираем геометрию
    if HAS_OSMTOGEOJSON:
        # Используем библиотеку для конвертации
        try:
            geojson_data = osmtogeojson.json_to_geojson(osm_data)
            if geojson_data and 'features' in geojson_data and len(geojson_data['features']) > 0:
                geom_json = geojson_data['features'][0]['geometry']
            else:
                geom_json = None
        except Exception as e:
            print(f"  [WARN] osmtogeojson failed: {e}")
            geom_json = build_polygon_from_ways(osm_data, district.osm_id)
    else:
        geom_json = build_polygon_from_ways(osm_data, district.osm_id)
    
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
    
    time.sleep(1)  # Задержка между запросами

print()
print(f"Исправлено районов: {fixed_count} из {len(problematic)}")

db.close()
