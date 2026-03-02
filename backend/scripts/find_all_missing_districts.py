"""Aggressive search for ALL missing district geometries."""
import sys
import time
import json
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from app.core.config import settings


def get_engine():
    return create_engine(settings.DATABASE_URL)


def get_missing_districts():
    """Get districts without geometry."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT d.id, d.name, r.name as region_name
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE d.geom IS NULL
            ORDER BY r.name, d.name
        """)).fetchall()
    return result


def search_nominatim(query, polygon=True):
    """Search Nominatim with various queries."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': query,
        'format': 'json',
        'polygon_geojson': 1 if polygon else 0,
        'limit': 5,
    }
    headers = {'User-Agent': 'ZoneMonitoring/1.0 (district geometry import)'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"      Nominatim error: {e}")
    return []


def search_overpass_by_name(name):
    """Search Overpass API by name for administrative boundary."""
    # Clean the name
    clean_name = name.replace('муниципальный район', '').replace('городской округ', '').strip()
    
    query = f"""
    [out:json][timeout:60];
    (
      relation["boundary"="administrative"]["name"~"{clean_name}"];
    );
    out geom;
    """
    
    url = "https://overpass-api.de/api/interpreter"
    try:
        resp = requests.post(url, data={'data': query}, timeout=90)
        if resp.status_code == 200:
            data = resp.json()
            # Find best match - prefer admin_level 6 or 7
            for level in ['6', '7', '8', '5']:
                for el in data.get('elements', []):
                    if el.get('tags', {}).get('admin_level') == level:
                        return el
            # Return first if no level match
            if data.get('elements'):
                return data['elements'][0]
    except Exception as e:
        print(f"      Overpass error: {e}")
    return None


def osm_relation_to_geojson(element):
    """Convert OSM relation to GeoJSON polygon."""
    if not element:
        return None
    
    if 'members' in element:
        # Build polygon from members
        outer_ways = []
        for member in element.get('members', []):
            if member.get('role') == 'outer' and member.get('type') == 'way':
                if 'geometry' in member:
                    coords = [[p['lon'], p['lat']] for p in member['geometry']]
                    outer_ways.append(coords)
        
        if outer_ways:
            if len(outer_ways) == 1:
                coords = outer_ways[0]
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                return {'type': 'Polygon', 'coordinates': [coords]}
            else:
                # MultiPolygon
                polygons = []
                for way in outer_ways:
                    if way[0] != way[-1]:
                        way.append(way[0])
                    polygons.append([way])
                return {'type': 'MultiPolygon', 'coordinates': polygons}
    
    if 'bounds' in element:
        bounds = element['bounds']
        coords = [[
            [bounds['minlon'], bounds['minlat']],
            [bounds['maxlon'], bounds['minlat']],
            [bounds['maxlon'], bounds['maxlat']],
            [bounds['minlon'], bounds['maxlat']],
            [bounds['minlon'], bounds['minlat']]
        ]]
        return {'type': 'Polygon', 'coordinates': coords}
    
    return None


def is_polygon_geometry(geojson):
    """Check if geometry is a polygon type."""
    if not geojson:
        return False
    gtype = geojson.get('type', '')
    return gtype in ('Polygon', 'MultiPolygon')


def update_district_geometry(district_id, geojson):
    """Update district geometry in database."""
    engine = get_engine()
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


# Special name mappings for known problematic districts
DISTRICT_SEARCH_VARIANTS = {
    # Якутия (ошибочно указаны как Тыва)
    "Абыйский муниципальный район": ["Абыйский улус", "Abyysky District", "Абыйский район Якутия"],
    "Алданский муниципальный район": ["Алданский район", "Aldan District", "Алданский район Якутия"],
    "Аллаиховский муниципальный район": ["Аллаиховский улус", "Allaikhovsky District"],
    "Амгинский муниципальный район": ["Амгинский улус", "Amginsky District"],
    "Анабарский национальный (долгано-эвенкийский) муниципальный район": ["Анабарский улус", "Anabar District"],
    "Булунский муниципальный район": ["Булунский улус", "Bulunsky District"],
    "Верхоянский муниципальный район": ["Верхоянский улус", "Verkhoyansk District"],
    "Вилюйский муниципальный район": ["Вилюйский улус", "Vilyuysky District"],
    "Жиганский национальный эвенкийский муниципальный район": ["Жиганский улус", "Zhigansky District"],
    "Кобяйский муниципальный район": ["Кобяйский улус", "Kobyaysky District"],
    "Мегино-Кангаласский муниципальный район": ["Мегино-Кангаласский улус", "Megino-Kangalassky District"],
    "Мирнинский муниципальный район": ["Мирнинский район", "Mirninsky District"],
    "Намский муниципальный район": ["Намский улус", "Namsky District"],
    "Нерюнгринский муниципальный район": ["Нерюнгринский район", "Neryungrinsky District"],
    "Нюрбинский муниципальный район": ["Нюрбинский улус", "Nyurbinsky District"],
    "Оймяконский муниципальный район": ["Оймяконский улус", "Oymyakonsky District"],
    "Олекминский муниципальный район": ["Олекминский улус", "Olekminsky District"],
    "Оленекский эвенкийский национальный муниципальный район": ["Оленекский улус", "Oleneksky District"],
    "Среднеколымский муниципальный район": ["Среднеколымский улус", "Srednekolymsky District"],
    "Таттинский муниципальный район": ["Таттинский улус", "Tattinsky District"],
    "Томпонский муниципальный район": ["Томпонский улус", "Tomponsky District"],
    "Усть-Алданский муниципальный район": ["Усть-Алданский улус", "Ust-Aldansky District"],
    "Усть-Майский муниципальный район": ["Усть-Майский улус", "Ust-Maysky District"],
    "Усть-Янский муниципальный район": ["Усть-Янский улус", "Ust-Yansky District"],
    "Хангаласский муниципальный район": ["Хангаласский улус", "Khangalassky District"],
    "Чурапчинский муниципальный район": ["Чурапчинский улус", "Churapchinsky District"],
    "Эвено-Бытантайский национальный муниципальный район": ["Эвено-Бытантайский улус", "Eveno-Bytantaysky District"],
    
    # Адыгея (ошибочно указаны как Ингушетия)
    "Кошехабльский муниципальный район": ["Кошехабльский район", "Koshekhablsky District", "Кошехабльский район Адыгея"],
    "Майкопский муниципальный район": ["Майкопский район", "Maykopsky District", "Майкопский район Адыгея"],
    "Тахтамукайский муниципальный район": ["Тахтамукайский район", "Takhtamukaysky District"],
    "Теучежский муниципальный район": ["Теучежский район", "Teuchezhsky District"],
    "Шовгеновский муниципальный район": ["Шовгеновский район", "Shovgenovsky District"],
    
    # ДНР
    "городской округ Горловка": ["Горловка", "Horlivka", "Gorlovka city"],
    "городской округ Дебальцево": ["Дебальцево", "Debaltseve", "Debaltsevo"],
    "городской округ Докучаевск": ["Докучаевск", "Dokuchaievsk", "Dokuchayevsk"],
    "городской округ Донецк": ["Донецк", "Donetsk city", "Донецк город"],
    "городской округ Енакиево": ["Енакиево", "Yenakiieve", "Enakievo"],
    "городской округ Иловайск": ["Иловайск", "Ilovaisk", "Ilovaysk"],
    "городской округ Краматорск": ["Краматорск", "Kramatorsk city"],
    "городской округ Макеевка": ["Макеевка", "Makiivka", "Makeyevka"],
    "городской округ Мариуполь": ["Мариуполь", "Mariupol city"],
    "городской округ Снежное": ["Снежное", "Snizhne", "Snezhnoye"],
    "городской округ Торез": ["Торез", "Torez", "Thorez"],
    "городской округ Харцызск": ["Харцызск", "Khartsyzk", "Khartsyzsk"],
    
    # Крым
    "Джанкойский муниципальный район": ["Джанкойский район", "Dzhankoysky District", "Джанкойський район"],
    "Кировский муниципальный район": ["Кировский район Крым", "Kirovsky District Crimea"],
    "Сакский муниципальный район": ["Сакский район", "Saksky District"],
    
    # Прочие
    "Кумторкалинский муниципальный район": ["Кумторкалинский район", "Kumtorkala District"],
    "Параньгинский муниципальный район": ["Параньгинский район", "Paranginsky District"],
    "Правобережный муниципальный район": ["Правобережный район", "Pravoberezhny District"],
    "Нурлатский муниципальный район": ["Нурлатский район", "Nurlatsky District"],
    "Сургутский муниципальный район": ["Сургутский район", "Surgutsky District"],
    "Ханты-Мансийский муниципальный район": ["Ханты-Мансийский район", "Khanty-Mansiysk District"],
}


def find_geometry_for_district(district_name, region_name):
    """Try multiple strategies to find geometry."""
    
    # Get search variants
    variants = DISTRICT_SEARCH_VARIANTS.get(district_name, [])
    
    # Add default variants
    clean_name = district_name.replace('муниципальный район', '').replace('городской округ', '').strip()
    all_variants = [
        f"{clean_name} район Россия",
        f"{clean_name} district Russia",
        f"{clean_name}, Россия",
        clean_name,
    ] + variants
    
    # Try Nominatim with each variant
    for variant in all_variants:
        print(f"      Trying: {variant[:50]}...", end=" ", flush=True)
        results = search_nominatim(variant)
        
        for r in results:
            if 'geojson' in r and is_polygon_geometry(r['geojson']):
                rtype = r.get('type', '')
                rclass = r.get('class', '')
                # Accept administrative boundaries
                if rclass == 'boundary' or rtype in ('administrative', 'city', 'town'):
                    print("Found!")
                    return r['geojson']
        print("no polygon")
        time.sleep(1.1)  # Rate limit
    
    # Try Overpass as last resort
    print(f"      Trying Overpass...", end=" ", flush=True)
    osm_el = search_overpass_by_name(district_name)
    if osm_el:
        geojson = osm_relation_to_geojson(osm_el)
        if geojson and is_polygon_geometry(geojson):
            print("Found!")
            return geojson
    print("not found")
    
    return None


def main():
    print("=" * 60)
    print("Поиск геометрий для ВСЕХ недостающих районов")
    print("=" * 60)
    
    districts = get_missing_districts()
    print(f"\nРайонов без геометрии: {len(districts)}\n")
    
    if not districts:
        print("Все районы имеют геометрию!")
        return
    
    updated = 0
    failed = []
    
    for d_id, d_name, r_name in districts:
        print(f"\n[{updated+1+len(failed)}/{len(districts)}] {d_name}")
        print(f"    Регион: {r_name}")
        
        geojson = find_geometry_for_district(d_name, r_name)
        
        if geojson:
            try:
                update_district_geometry(d_id, geojson)
                print(f"    -> СОХРАНЕНО")
                updated += 1
            except Exception as e:
                print(f"    -> ОШИБКА БД: {e}")
                failed.append((r_name, d_name, str(e)))
        else:
            print(f"    -> НЕ НАЙДЕНО")
            failed.append((r_name, d_name, "not found"))
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТ: Обновлено {updated} из {len(districts)}")
    print("=" * 60)
    
    if failed:
        print(f"\nНе удалось ({len(failed)}):")
        for region, name, reason in failed:
            print(f"  [{region}] {name}: {reason}")


if __name__ == "__main__":
    main()
