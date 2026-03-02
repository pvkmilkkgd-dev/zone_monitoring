"""
Заполнить дыры в Васильевском и Токмакском МО Запорожской области.
Дыры — это города Запорожье (Zaporiz'ka) и Токмак (Tokmats'ka),
которые в GADM отдельные, но в БД не существуют как ГО.
Вливаем их территорию в окружающие МО.
"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm41_UKR_2.json'
engine = sa.create_engine(settings.DATABASE_URL)


def main():
    print("=" * 70)
    print("ЗАПОЛНЕНИЕ ДЫР В ЗАПОРОЖСКОЙ ОБЛАСТИ")
    print("=" * 70)

    # Load cached GADM
    with open(GADM_CACHE, 'r', encoding='utf-8') as f:
        gadm = json.load(f)

    # Find the two city features
    city_to_mo = {
        "Zaporiz'ka": "Васильевский муниципальный округ",    # г. Запорожье -> Васильевский
        "Tokmats'ka": "Токмакский муниципальный округ",      # г. Токмак -> Токмакский
    }

    city_geojsons = {}
    for f in gadm.get('features', []):
        props = f.get('properties', {})
        if 'Zaporiz' not in props.get('NAME_1', ''):
            continue
        name2 = props.get('NAME_2', '')
        if name2 in city_to_mo:
            city_geojsons[name2] = json.dumps(f['geometry'])
            print(f"  Найден GADM: {name2}")

    with engine.begin() as conn:
        region_id = conn.execute(text(
            "SELECT id FROM regions WHERE name ILIKE '%Запорож%'"
        )).scalar()

        for gadm_name, db_name in city_to_mo.items():
            geojson = city_geojsons.get(gadm_name)
            if not geojson:
                print(f"  [!] Не найден GADM feature: {gadm_name}")
                continue

            # Get district ID
            d_id = conn.execute(text(
                "SELECT id FROM districts WHERE region_id = :rid AND name = :n"
            ), {"rid": str(region_id), "n": db_name}).scalar()

            if not d_id:
                print(f"  [!] Район не найден: {db_name}")
                continue

            # Show before
            r = conn.execute(text("""
                SELECT ST_NPoints(geom), ROUND((ST_Area(geom::geography)/1e6)::numeric, 1)
                FROM districts WHERE id = :id
            """), {"id": str(d_id)})
            before = r.fetchone()
            print(f"\n  {db_name}:")
            print(f"    ДО:    {before[0]} pts, {before[1]} km²")

            # Merge city geometry into MO
            conn.execute(text("""
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(
                    ST_Union(
                        geom,
                        ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))
                    )
                ))
                WHERE id = :id
            """), {"g": geojson, "id": str(d_id)})

            # Show after
            r = conn.execute(text("""
                SELECT ST_NPoints(geom), ROUND((ST_Area(geom::geography)/1e6)::numeric, 1)
                FROM districts WHERE id = :id
            """), {"id": str(d_id)})
            after = r.fetchone()
            print(f"    ПОСЛЕ: {after[0]} pts, {after[1]} km²")

    print("\nГотово!")


if __name__ == "__main__":
    main()
