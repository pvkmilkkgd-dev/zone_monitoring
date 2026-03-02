"""
Скрипт для скачивания и загрузки геометрии регионов России.

Использование:
    python download_region_geometry.py --list                    # Показать все регионы
    python download_region_geometry.py --download "Название"     # Скачать геометрию региона
    python download_region_geometry.py --download-all            # Скачать все регионы
    python download_region_geometry.py --load file.geojson       # Загрузить из файла
    python download_region_geometry.py --fix-region "Название"   # Исправить конкретный регион

Источники геометрии:
    1. OSM Nominatim (по умолчанию)
    2. Overpass API (для сложных случаев)
    3. Локальный GeoJSON файл
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

# Добавляем путь к приложению
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

# Директория для кэширования
CACHE_DIR = Path(__file__).parent / "geodata" / "regions_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# OSM Relation IDs для регионов России (admin_level=4)
# Источник: https://wiki.openstreetmap.org/wiki/Russia
REGION_OSM_IDS = {
    # Республики
    "Республика Адыгея": 253256,
    "Республика Алтай": 145194,
    "Республика Башкортостан": 77665,
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
    "Республика Северная Осетия — Алания": 110032,
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
    "Волгоградская область": 77666,
    "Вологодская область": 115106,
    "Воронежская область": 72181,
    "Донецкая Народная Республика": 71973,  # Donetsk Oblast
    "Еврейская автономная область": 147167,
    "Запорожская область": 71980,
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
    "Луганская Народная Республика": 71971,  # Luhansk Oblast
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
    "Херсонская область": 71022,
    "Челябинская область": 77687,
    "Ярославская область": 81994,
    
    # Города федерального значения
    "город Москва": 102269,
    "город Санкт-Петербург": 337422,
    "город Севастополь": 1574364,
    
    # Автономные округа
    "Ненецкий автономный округ": 274048,
    "Ханты-Мансийский автономный округ — Югра": 140296,
    "Чукотский автономный округ": 151232,
    "Ямало-Ненецкий автономный округ": 191706,
}


def get_engine():
    """Создать подключение к БД."""
    return create_engine(settings.DATABASE_URL)


def list_regions():
    """Показать список регионов в БД."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT name, 
                   CASE WHEN geom IS NOT NULL THEN 'Да' ELSE 'Нет' END as has_geom,
                   CASE WHEN geom IS NOT NULL THEN 
                       ROUND(ST_Area(geom::geography) / 1000000)::text || ' км²'
                   ELSE '-' END as area
            FROM regions
            ORDER BY name
        """)).fetchall()
        
        print(f"\n{'Регион':<50} {'Геометрия':<10} {'Площадь':<15}")
        print("-" * 75)
        for row in result:
            print(f"{row[0]:<50} {row[1]:<10} {row[2]:<15}")
        print(f"\nВсего: {len(result)} регионов")


def download_from_nominatim(region_name: str, osm_id: int) -> dict | None:
    """Скачать геометрию через Nominatim."""
    cache_file = CACHE_DIR / f"nominatim_{osm_id}.geojson"
    
    if cache_file.exists():
        print(f"  [кэш] Загружаю из кэша...")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        "osm_ids": f"R{osm_id}",
        "format": "geojson",
        "polygon_geojson": 1,
    }
    headers = {
        "User-Agent": "ZoneMonitoring/1.0 (region geometry download)"
    }
    
    print(f"  Запрос к Nominatim (OSM ID: {osm_id})...", end=" ", flush=True)
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("features"):
            # Сохраняем в кэш
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            print("OK")
            return data
        else:
            print("Нет данных")
            return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def download_from_overpass(region_name: str, osm_id: int) -> dict | None:
    """Скачать геометрию через Overpass API."""
    cache_file = CACHE_DIR / f"overpass_{osm_id}.json"
    
    if cache_file.exists():
        print(f"  [кэш] Загружаю из кэша Overpass...")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    query = f"""
    [out:json][timeout:300];
    rel({osm_id});
    out geom;
    """
    
    print(f"  Запрос к Overpass API (OSM ID: {osm_id})...", end=" ", flush=True)
    
    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=300
        )
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("elements"):
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            print("OK")
            return data
        else:
            print("Нет данных")
            return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def overpass_to_geojson(data: dict) -> dict | None:
    """Конвертировать данные Overpass в GeoJSON."""
    if not data.get("elements"):
        return None
    
    relation = data["elements"][0]
    members = relation.get("members", [])
    
    # Собираем все ways с геометрией
    outer_ways = []
    inner_ways = []
    
    for member in members:
        if member.get("type") != "way":
            continue
        
        geometry = member.get("geometry", [])
        if not geometry:
            continue
        
        coords = [[pt["lon"], pt["lat"]] for pt in geometry]
        role = member.get("role", "outer")
        
        if role == "outer":
            outer_ways.append(coords)
        elif role == "inner":
            inner_ways.append(coords)
    
    if not outer_ways:
        return None
    
    # Пытаемся объединить ways в кольца
    def merge_ways(ways):
        """Объединить ways в замкнутые кольца."""
        if not ways:
            return []
        
        rings = []
        remaining = ways.copy()
        
        while remaining:
            ring = remaining.pop(0)
            changed = True
            
            while changed:
                changed = False
                for i, way in enumerate(remaining):
                    # Проверяем, можно ли присоединить way к ring
                    if ring[-1] == way[0]:
                        ring = ring + way[1:]
                        remaining.pop(i)
                        changed = True
                        break
                    elif ring[-1] == way[-1]:
                        ring = ring + way[-2::-1]
                        remaining.pop(i)
                        changed = True
                        break
                    elif ring[0] == way[-1]:
                        ring = way + ring[1:]
                        remaining.pop(i)
                        changed = True
                        break
                    elif ring[0] == way[0]:
                        ring = way[::-1] + ring[1:]
                        remaining.pop(i)
                        changed = True
                        break
            
            # Замыкаем кольцо
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            
            if len(ring) >= 4:
                rings.append(ring)
        
        return rings
    
    outer_rings = merge_ways(outer_ways)
    inner_rings = merge_ways(inner_ways)
    
    if not outer_rings:
        return None
    
    # Создаём MultiPolygon
    polygons = []
    for outer in outer_rings:
        polygon = [outer]
        # TODO: добавить inner rings к соответствующим outer
        polygons.append(polygon)
    
    if len(polygons) == 1:
        geometry = {
            "type": "Polygon",
            "coordinates": polygons[0]
        }
    else:
        geometry = {
            "type": "MultiPolygon",
            "coordinates": polygons
        }
    
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": relation.get("tags", {}).get("name", "")},
            "geometry": geometry
        }]
    }


def update_region_geometry(region_name: str, geojson: dict):
    """Обновить геометрию региона в БД."""
    if not geojson.get("features"):
        print(f"  ! Нет features в GeoJSON")
        return False
    
    feature = geojson["features"][0]
    geometry = feature.get("geometry")
    
    if not geometry:
        print(f"  ! Нет geometry в feature")
        return False
    
    geom_json = json.dumps(geometry, ensure_ascii=False)
    
    engine = get_engine()
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                UPDATE regions SET
                    geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                    geom_simplified = ST_SimplifyPreserveTopology(
                        ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 3)),
                        0.01
                    ),
                    bbox = ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                    updated_at = NOW()
                WHERE name = :name
                RETURNING id
            """), {"geom": geom_json, "name": region_name})
            conn.commit()
            
            row = result.fetchone()
            if row:
                print(f"  ✓ Геометрия обновлена")
                return True
            else:
                print(f"  ! Регион '{region_name}' не найден в БД")
                return False
        except Exception as e:
            conn.rollback()
            print(f"  ! Ошибка БД: {e}")
            return False


def download_region(region_name: str, source: str = "nominatim"):
    """Скачать и загрузить геометрию для одного региона."""
    print(f"\n=== {region_name} ===")
    
    osm_id = REGION_OSM_IDS.get(region_name)
    if not osm_id:
        print(f"  ! OSM ID не найден для региона")
        return False
    
    geojson = None
    
    if source == "nominatim":
        geojson = download_from_nominatim(region_name, osm_id)
    elif source == "overpass":
        data = download_from_overpass(region_name, osm_id)
        if data:
            geojson = overpass_to_geojson(data)
    
    if geojson:
        return update_region_geometry(region_name, geojson)
    
    return False


def download_all_regions(source: str = "nominatim", delay: float = 1.5):
    """Скачать геометрию для всех регионов."""
    print(f"\nСкачивание всех регионов (источник: {source})")
    print(f"Задержка между запросами: {delay} сек")
    print("=" * 60)
    
    success = 0
    failed = []
    
    for region_name in sorted(REGION_OSM_IDS.keys()):
        if download_region(region_name, source):
            success += 1
        else:
            failed.append(region_name)
        
        time.sleep(delay)
    
    print("\n" + "=" * 60)
    print(f"Успешно: {success}")
    print(f"Ошибки: {len(failed)}")
    
    if failed:
        print("\nНе удалось загрузить:")
        for name in failed:
            print(f"  - {name}")


def load_from_file(filepath: str, region_name: str = None):
    """Загрузить геометрию из GeoJSON файла."""
    path = Path(filepath)
    if not path.exists():
        print(f"Файл не найден: {filepath}")
        return False
    
    print(f"\nЗагрузка из файла: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
    
    if region_name:
        # Загружаем для конкретного региона
        return update_region_geometry(region_name, geojson)
    else:
        # Если это FeatureCollection, обновляем все регионы по имени
        if geojson.get("type") == "FeatureCollection":
            success = 0
            for feature in geojson.get("features", []):
                name = feature.get("properties", {}).get("name")
                if name:
                    single_geojson = {
                        "type": "FeatureCollection",
                        "features": [feature]
                    }
                    if update_region_geometry(name, single_geojson):
                        success += 1
            print(f"\nОбновлено регионов: {success}")
            return success > 0
        else:
            print("Укажите имя региона для загрузки одиночной геометрии")
            return False


def fix_region(region_name: str):
    """Попытаться исправить геометрию региона разными способами."""
    print(f"\n=== Исправление: {region_name} ===")
    
    # Сначала пробуем Nominatim
    print("\n1. Пробуем Nominatim...")
    if download_region(region_name, "nominatim"):
        return True
    
    # Затем Overpass
    print("\n2. Пробуем Overpass API...")
    time.sleep(2)
    if download_region(region_name, "overpass"):
        return True
    
    print(f"\n! Не удалось исправить геометрию для '{region_name}'")
    print("  Попробуйте загрузить GeoJSON вручную:")
    print(f"  python {Path(__file__).name} --load file.geojson --name \"{region_name}\"")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Скачивание и загрузка геометрии регионов России",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python download_region_geometry.py --list
  python download_region_geometry.py --download "Республика Крым"
  python download_region_geometry.py --download "Донецкая Народная Республика" --source overpass
  python download_region_geometry.py --fix-region "Херсонская область"
  python download_region_geometry.py --load regions.geojson
  python download_region_geometry.py --load region.geojson --name "Запорожская область"
        """
    )
    
    parser.add_argument("--list", action="store_true", help="Показать список регионов")
    parser.add_argument("--download", metavar="NAME", help="Скачать геометрию для региона")
    parser.add_argument("--download-all", action="store_true", help="Скачать все регионы")
    parser.add_argument("--source", choices=["nominatim", "overpass"], default="nominatim",
                        help="Источник данных (по умолчанию: nominatim)")
    parser.add_argument("--load", metavar="FILE", help="Загрузить из GeoJSON файла")
    parser.add_argument("--name", metavar="NAME", help="Имя региона (для --load)")
    parser.add_argument("--fix-region", metavar="NAME", help="Исправить геометрию региона")
    parser.add_argument("--delay", type=float, default=1.5, help="Задержка между запросами (сек)")
    
    args = parser.parse_args()
    
    if args.list:
        list_regions()
    elif args.download:
        download_region(args.download, args.source)
    elif args.download_all:
        download_all_regions(args.source, args.delay)
    elif args.load:
        load_from_file(args.load, args.name)
    elif args.fix_region:
        fix_region(args.fix_region)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
