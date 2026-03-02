# -*- coding: utf-8 -*-
"""
Загрузка геометрии районов Республики Дагестан из GeoJSON файла.

Поддерживает данные из ГИС ЖКХ, JSM, GADM, OSM и других источников.
Сопоставление по названиям районов (с учётом разных форматов: муниципальный район, ГО и т.д.)

Usage:
    python scripts/load_dagestan_geojson.py path/to/dagestan_districts.geojson

    # Или с указанием региона (по умолчанию Республика Дагестан):
    python scripts/load_dagestan_geojson.py path/to/file.geojson "Республика Дагестан"

Example:
    python scripts/load_dagestan_geojson.py C:\Downloads\dagestan_rayony.geojson
"""
import sys
import io
import json
import re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

REGION = "Республика Дагестан"

# Возможные поля с названием района (ГИС ЖКХ, JSM, GADM, OSM и др.)
NAME_KEYS = [
    'name', 'NAME', 'name_ru', 'name_1', 'name_2',
    'NAME_2', 'NL_NAME_2', 'наименование', 'mun_name', 'municipality_name',
    'district', 'raion', 'rayon', 'mo_name', 'oktmo_name',
]


def normalize(name):
    """Нормализация названия для сопоставления."""
    if not name or not isinstance(name, str):
        return ''
    n = name.lower().strip()
    # Убираем типичные суффиксы
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'город', 'г.', 'с п', 'мр', 'мо', 'го']:
        n = n.replace(w, '')
    n = n.replace('-', ' ').replace('ё', 'е').replace('  ', ' ')
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def extract_name(props):
    """Извлечь название района из properties."""
    for key in NAME_KEYS:
        val = props.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return ''


def match_district(osm_name, db_names, used_db):
    """Сопоставить название из файла с районом в БД."""
    osm_norm = normalize(osm_name)
    available = [n for n in db_names if n not in used_db]

    # Точное совпадение
    for db_name in available:
        if normalize(db_name) == osm_norm:
            return db_name

    # Частичное (одно в другом)
    for db_name in available:
        db_norm = normalize(db_name)
        if osm_norm and db_norm and (osm_norm in db_norm or db_norm in osm_norm):
            return db_name

    # По первому слову (для "Хунзахский район" vs "Хунзахский муниципальный район")
    osm_first = (osm_norm.split() or [''])[0]
    if len(osm_first) > 2:
        for db_name in available:
            db_norm = normalize(db_name)
            db_first = (db_norm.split() or [''])[0]
            if osm_first == db_first:
                return db_name

    return None


def load_dagestan_geojson(file_path, region_name=REGION):
    """Загрузить геометрию районов Дагестана из GeoJSON."""
    path = Path(file_path)
    if not path.exists():
        print(f"Файл не найден: {file_path}")
        return False

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    features = data.get('features', [])
    if not features:
        print("В файле нет features!")
        return False

    sample = features[0].get('properties', {})
    print(f"Features в файле: {len(features)}")
    print(f"Properties: {list(sample.keys())}")

    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        region = conn.execute(text(
            "SELECT id FROM regions WHERE name = :name"
        ), {"name": region_name}).fetchone()

        if not region:
            print(f"Регион '{region_name}' не найден в БД!")
            return False

        region_id = str(region[0])
        districts = conn.execute(text("""
            SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name
        """), {"rid": region_id}).fetchall()

    db_names = [r[1] for r in districts]
    db_by_name = {r[1]: str(r[0]) for r in districts}
    used_db = set()

    updated = 0
    not_found = []
    errors = []

    for feat in features:
        props = feat.get('properties', {})
        geom = feat.get('geometry')

        if not geom:
            continue

        name = extract_name(props)
        if not name:
            continue

        db_match = match_district(name, db_names, used_db)
        if db_match:
            district_id = db_by_name[db_match]
            used_db.add(db_match)
            geojson_str = json.dumps(geom)

            # Polygon -> MultiPolygon
            if geom.get('type') == 'Polygon':
                geom = {'type': 'MultiPolygon', 'coordinates': [geom['coordinates']]}
                geojson_str = json.dumps(geom)

            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE districts
                        SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))),
                            geom_simplified = ST_SimplifyPreserveTopology(
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))),
                                0.005
                            )
                        WHERE id = :id
                    """), {'gj': geojson_str, 'id': district_id})
                updated += 1
                print(f"  + {name} -> {db_match}")
            except Exception as e:
                errors.append((name, str(e)))
                print(f"  ! {name}: {e}")
        else:
            not_found.append(name)

    print(f"\nОбновлено: {updated}")
    print(f"Не сопоставлено: {len(not_found)}")
    if errors:
        print(f"Ошибки: {len(errors)}")

    if not_found:
        print("\nНе найдены в БД:")
        for n in not_found[:30]:
            print(f"  - {n}")
        if len(not_found) > 30:
            print(f"  ... и ещё {len(not_found) - 30}")

    return updated > 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    file_path = sys.argv[1]
    region_name = sys.argv[2] if len(sys.argv) > 2 else REGION

    print(f"Загрузка геометрии районов: {region_name}")
    print(f"Файл: {file_path}\n")

    success = load_dagestan_geojson(file_path, region_name)
    sys.exit(0 if success else 1)
