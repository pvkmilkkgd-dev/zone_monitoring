"""
Скрипт для загрузки всех 89 регионов РФ из OpenStreetMap (Overpass API)
с официальными названиями из Excel.
"""
import os
import sys
import json
import time
import requests
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

DATA_DIR = Path(__file__).parent / "geodata"
DATA_DIR.mkdir(exist_ok=True)

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def get_russia_regions_from_overpass() -> list:
    """Получить все регионы России из Overpass API."""
    cache_file = DATA_DIR / "osm_russia_regions.json"
    
    if cache_file.exists():
        print("  Используем кэшированные данные OSM")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    print("  Запрос к Overpass API (это может занять несколько минут)...")
    
    # Запрос для получения всех регионов России (admin_level=4)
    query = """
    [out:json][timeout:300];
    area["ISO3166-1"="RU"]->.russia;
    (
      relation["admin_level"="4"]["boundary"="administrative"](area.russia);
    );
    out body;
    >;
    out skel qt;
    """
    
    response = requests.post(OVERPASS_URL, data={'data': query}, timeout=600)
    response.raise_for_status()
    data = response.json()
    
    # Сохраняем в кэш
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    
    print(f"  Получено элементов: {len(data.get('elements', []))}")
    return data


def get_region_geometry_from_overpass(region_id: int) -> dict:
    """Получить геометрию региона по OSM relation ID."""
    cache_file = DATA_DIR / f"osm_region_{region_id}.json"
    
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    query = f"""
    [out:json][timeout:120];
    rel({region_id});
    out geom;
    """
    
    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, timeout=180)
        response.raise_for_status()
        data = response.json()
        
        # Сохраняем в кэш
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        return data
    except Exception as e:
        print(f"    Ошибка загрузки геометрии для {region_id}: {e}")
        return None


def osm_to_geojson_polygon(members: list, nodes_map: dict) -> dict:
    """Конвертировать OSM way members в GeoJSON Polygon/MultiPolygon."""
    # Собираем все внешние и внутренние кольца
    outer_rings = []
    inner_rings = []
    
    for member in members:
        if member.get('type') != 'way':
            continue
        
        role = member.get('role', 'outer')
        geometry = member.get('geometry', [])
        
        if not geometry:
            continue
        
        coords = [[pt['lon'], pt['lat']] for pt in geometry]
        
        if role == 'outer':
            outer_rings.append(coords)
        elif role == 'inner':
            inner_rings.append(coords)
    
    if not outer_rings:
        return None
    
    # Объединяем кольца в полигоны
    # Для простоты создаём MultiPolygon
    polygons = []
    for ring in outer_rings:
        # Замыкаем кольцо если нужно
        if ring and ring[0] != ring[-1]:
            ring.append(ring[0])
        if len(ring) >= 4:  # Минимум 4 точки для полигона
            polygons.append([ring])
    
    if len(polygons) == 0:
        return None
    elif len(polygons) == 1:
        return {
            "type": "Polygon",
            "coordinates": polygons[0]
        }
    else:
        return {
            "type": "MultiPolygon",
            "coordinates": polygons
        }


def load_excel_regions(excel_path: str) -> dict:
    """Загрузить названия регионов из Excel."""
    df = pd.read_excel(excel_path)
    df.columns = ['region_name', 'district_name', 'admin_center']
    
    # Уникальные регионы
    regions = df['region_name'].unique().tolist()
    return {normalize_region_name(r): r for r in regions}


def normalize_region_name(name: str) -> str:
    """Нормализовать название региона для сопоставления."""
    if not name:
        return ""
    name = name.lower().strip()
    # Убираем типичные части названий
    replacements = [
        "республика ", " республика",
        " область", " край", 
        " автономный округ", " автономная область",
        "город ", " - ", "-", "ё"
    ]
    for r in replacements:
        name = name.replace(r, " " if r in [" - ", "-"] else "")
    # Специальные замены
    name = name.replace("ё", "е")
    return " ".join(name.split()).strip()


# Полный список всех 89 регионов РФ с их OSM relation ID
RUSSIA_REGIONS = {
    # Республики
    "Республика Адыгея": 253256,
    "Республика Алтай": 145194,
    "Республика Башкортостан": 77677,
    "Республика Бурятия": 145729,
    "Республика Дагестан": 109876,
    "Республика Ингушетия": 253252,
    "Кабардино-Балкарская Республика": 109879,
    "Республика Калмыкия": 108083,
    "Карачаево-Черкесская Республика": 109878,
    "Республика Карелия": 393980,
    "Республика Коми": 115136,
    "Республика Крым": 3795586,
    "Республика Марий Эл": 115114,
    "Республика Мордовия": 115116,
    "Республика Саха (Якутия)": 151231,
    "Республика Северная Осетия - Алания": 110032,
    "Республика Татарстан": 79374,
    "Республика Тыва": 145195,
    "Удмуртская Республика": 115134,
    "Республика Хакасия": 190911,
    "Чеченская Республика": 253253,
    "Чувашская Республика": 80513,
    
    # Края
    "Алтайский край": 144764,
    "Забайкальский край": 145730,
    "Камчатский край": 151233,
    "Краснодарский край": 108082,
    "Красноярский край": 190090,
    "Пермский край": 115135,
    "Приморский край": 151225,
    "Ставропольский край": 108081,
    "Хабаровский край": 151223,
    
    # Области
    "Амурская область": 147166,
    "Архангельская область": 140337,
    "Астраханская область": 112819,
    "Белгородская область": 83184,
    "Брянская область": 81997,
    "Владимирская область": 72197,
    "Волгоградская область": 77665,
    "Вологодская область": 115106,
    "Воронежская область": 72181,
    "Ивановская область": 85617,
    "Иркутская область": 145454,
    "Калининградская область": 103906,
    "Калужская область": 81995,
    "Кемеровская область": 144763,
    "Кировская область": 115100,
    "Костромская область": 85963,
    "Курганская область": 140290,
    "Курская область": 72223,
    "Ленинградская область": 176095,
    "Липецкая область": 72169,
    "Магаданская область": 151228,
    "Московская область": 51490,
    "Мурманская область": 2099216,
    "Нижегородская область": 72195,
    "Новгородская область": 89331,
    "Новосибирская область": 140294,
    "Омская область": 140292,
    "Оренбургская область": 77669,
    "Орловская область": 72224,
    "Пензенская область": 72182,
    "Псковская область": 155262,
    "Ростовская область": 85606,
    "Рязанская область": 71950,
    "Самарская область": 72194,
    "Саратовская область": 72193,
    "Сахалинская область": 394235,
    "Свердловская область": 79379,
    "Смоленская область": 81996,
    "Тамбовская область": 72180,
    "Тверская область": 2095259,
    "Томская область": 140295,
    "Тульская область": 81993,
    "Тюменская область": 140291,
    "Ульяновская область": 72192,
    "Челябинская область": 77687,
    "Ярославская область": 81994,
    
    # Города федерального значения
    "город Москва": 102269,
    "город Санкт-Петербург": 337422,
    "город Севастополь": 1574364,
    
    # Автономные округа
    "Ненецкий автономный округ": 274048,
    "Ханты-Мансийский автономный округ - Югра": 140296,
    "Чукотский автономный округ": 151232,
    "Ямало-Ненецкий автономный округ": 191706,
    
    # Автономная область
    "Еврейская автономная область": 147167,
    
    # Новые регионы (2022)
    "Донецкая Народная Республика": 5765844,
    "Луганская Народная Республика": 5765468,
    "Запорожская область": 71980,
    "Херсонская область": 71973,
}


def import_all_regions(engine, excel_regions: dict):
    """Импортировать все 89 регионов РФ."""
    print(f"\n=== Импорт {len(RUSSIA_REGIONS)} регионов РФ ===")
    
    with engine.connect() as conn:
        # Очищаем таблицу
        conn.execute(text("TRUNCATE TABLE regions CASCADE"))
        conn.commit()
        print("Таблица regions очищена")
        
        imported = 0
        errors = []
        
        for region_name, osm_id in RUSSIA_REGIONS.items():
            # Ищем официальное название из Excel
            norm_name = normalize_region_name(region_name)
            official_name = None
            for excel_norm, excel_name in excel_regions.items():
                if norm_name in excel_norm or excel_norm in norm_name:
                    official_name = excel_name
                    break
            
            # Используем Excel название если найдено, иначе стандартное
            final_name = official_name if official_name else region_name
            
            print(f"  [{imported+1}/{len(RUSSIA_REGIONS)}] {final_name}...", end=" ", flush=True)
            
            # Получаем геометрию
            geom_data = get_region_geometry_from_overpass(osm_id)
            
            if not geom_data or not geom_data.get('elements'):
                print("НЕТ ДАННЫХ - вставляем без геометрии")
                errors.append(final_name)
                # Вставляем без геометрии
                sql = text("""
                    INSERT INTO regions (id, name, name_original, code, created_at, updated_at, is_active)
                    VALUES (gen_random_uuid(), :name, :name_original, :code, NOW(), NOW(), true)
                """)
                conn.execute(sql, {
                    'name': final_name,
                    'name_original': region_name,
                    'code': f'OSM_{osm_id}'
                })
                conn.commit()
                imported += 1
                continue
            
            # Извлекаем геометрию из relation
            relation = geom_data['elements'][0]
            members = relation.get('members', [])
            
            geom = osm_to_geojson_polygon(members, {})
            
            if not geom:
                print("ОШИБКА КОНВЕРТАЦИИ - вставляем без геометрии")
                errors.append(final_name)
                # Вставляем без геометрии
                sql = text("""
                    INSERT INTO regions (id, name, name_original, code, created_at, updated_at, is_active)
                    VALUES (gen_random_uuid(), :name, :name_original, :code, NOW(), NOW(), true)
                """)
                conn.execute(sql, {
                    'name': final_name,
                    'name_original': region_name,
                    'code': f'OSM_{osm_id}'
                })
                conn.commit()
                imported += 1
                continue
            
            geom_json = json.dumps(geom, ensure_ascii=False)
            
            # Используем ST_Multi и ST_CollectionExtract для конвертации в MultiPolygon
            sql = text("""
                INSERT INTO regions (id, name, name_original, code, geom, geom_simplified, bbox, created_at, updated_at, is_active)
                VALUES (
                    gen_random_uuid(),
                    :name,
                    :name_original,
                    :code,
                    ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                    ST_SimplifyPreserveTopology(
                        ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                        0.01
                    ),
                    ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                    NOW(),
                    NOW(),
                    true
                )
            """)
            
            try:
                conn.execute(sql, {
                    'name': final_name,
                    'name_original': region_name,
                    'code': f'OSM_{osm_id}',
                    'geom': geom_json
                })
                conn.commit()  # Коммитим каждую запись отдельно
                print("OK")
            except Exception as e:
                conn.rollback()  # Откатываем транзакцию при ошибке
                print(f"ОШИБКА ГЕОМЕТРИИ, вставляем без неё")
                errors.append(final_name)
                # Вставляем без геометрии
                sql2 = text("""
                    INSERT INTO regions (id, name, name_original, code, created_at, updated_at, is_active)
                    VALUES (gen_random_uuid(), :name, :name_original, :code, NOW(), NOW(), true)
                """)
                conn.execute(sql2, {
                    'name': final_name,
                    'name_original': region_name,
                    'code': f'OSM_{osm_id}'
                })
                conn.commit()
            
            imported += 1
            
            # Пауза чтобы не перегружать API
            time.sleep(0.3)
        
    print(f"\nИмпортировано регионов: {imported}")
    if errors:
        print(f"Ошибки ({len(errors)}): {errors}")


def main():
    excel_path = r"C:\Users\Lucky\Downloads\123.xlsx"
    
    print("=" * 60)
    print("ИМПОРТ 89 РЕГИОНОВ РФ ИЗ OPENSTREETMAP")
    print("=" * 60)
    
    engine = create_engine(settings.DATABASE_URL)
    print(f"\nПодключение к БД: OK")
    
    # Загружаем названия из Excel
    print("\n1. Загрузка названий из Excel...")
    excel_regions = load_excel_regions(excel_path)
    print(f"   Найдено регионов в Excel: {len(excel_regions)}")
    
    # Импортируем регионы
    print("\n2. Загрузка геометрии из Overpass API...")
    import_all_regions(engine, excel_regions)
    
    print("\n" + "=" * 60)
    print("ИМПОРТ РЕГИОНОВ ЗАВЕРШЁН!")
    print("=" * 60)


if __name__ == "__main__":
    main()
