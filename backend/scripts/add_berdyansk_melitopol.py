"""
Добавить Бердянский МО и Мелитопольский МО в Запорожскую область.
Геометрия из GADM: Berdians'kyi и Melitopol's'kyi.
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import uuid
import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm41_UKR_2.json'
engine = sa.create_engine(settings.DATABASE_URL)

NEW_DISTRICTS = {
    "Бердянский муниципальный округ": "Berdians'kyi",
    "Мелитопольский муниципальный округ": "Melitopol's'kyi",
}


def main():
    print("=" * 70)
    print("ДОБАВЛЕНИЕ БЕРДЯНСКОГО И МЕЛИТОПОЛЬСКОГО МО")
    print("=" * 70)

    # Load GADM
    with open(GADM_CACHE, 'r', encoding='utf-8') as f:
        gadm = json.load(f)

    gadm_features = {}
    for feat in gadm.get('features', []):
        props = feat.get('properties', {})
        if 'Zaporiz' in props.get('NAME_1', ''):
            gadm_features[props.get('NAME_2', '')] = feat

    with engine.begin() as conn:
        region_id = conn.execute(text(
            "SELECT id FROM regions WHERE name ILIKE '%Запорож%'"
        )).scalar()
        print(f"Регион: {region_id}")

        for db_name, gadm_name in NEW_DISTRICTS.items():
            # Check if already exists
            existing = conn.execute(text(
                "SELECT id FROM districts WHERE region_id = :rid AND name = :n"
            ), {"rid": str(region_id), "n": db_name}).fetchone()

            if existing:
                d_id = str(existing[0])
                print(f"\n  {db_name}: уже существует ({d_id}), обновляем геометрию")
            else:
                d_id = str(uuid.uuid4())
                conn.execute(text("""
                    INSERT INTO districts (id, name, region_id)
                    VALUES (:id, :name, :rid)
                """), {"id": d_id, "name": db_name, "rid": str(region_id)})
                print(f"\n  {db_name}: создан ({d_id})")

            # Load geometry from GADM
            feat = gadm_features.get(gadm_name)
            if not feat:
                print(f"    [!] GADM feature '{gadm_name}' не найден!")
                continue

            geojson = json.dumps(feat['geometry'])
            conn.execute(text("""
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                WHERE id = :id
            """), {"g": geojson, "id": d_id})

            r = conn.execute(text("""
                SELECT ST_NPoints(geom), ROUND((ST_Area(geom::geography)/1e6)::numeric, 1)
                FROM districts WHERE id = :id
            """), {"id": d_id})
            row = r.fetchone()
            print(f"    Геометрия: {row[0]} pts, {row[1]} km²")

    print("\nГотово!")


if __name__ == "__main__":
    main()
