# -*- coding: utf-8 -*-
"""
Загрузка геометрии Чукотского АО из GADM Russia level 2.
Учёт реорганизации районов:
- Беринговский район → Анадырский МО (объединён)
- Шмидтовский район → МО Певек (объединён с Чаунским)
- Иультинский район → МО Эгвекинот (переименован)
- Чаунский район → МО Певек (переименован)
- городской округ Анадырь — нет отдельного GADM, город внутри Анадырского
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm_russia_level2.json'
REGION = 'Чукотский автономный округ'

# GADM NAME_2 → название в БД
# Несколько GADM районов могут сливаться в один БД район (merge)
GADM_TO_DB = {
    "Anadyrskiyrayon":       "Анадырский муниципальный округ",
    "Beringovskiyrayon":     "Анадырский муниципальный округ",        # объединён
    "Bilibinskiyrayon":      "Билибинский муниципальный район",
    "Chaunskiyrayon":        "муниципальный округ Певек",             # переименован
    "Chukotskiyrayon":       "Чукотский муниципальный район",
    "Iyul'tinskiyrayon":     "муниципальный округ Эгвекинот",         # переименован
    "Providenskiyrayon":     "Провиденский муниципальный округ",
    "Shmidtovskiyrayon":     "муниципальный округ Певек",             # объединён с Чаунским
}

engine = create_engine(settings.DATABASE_URL)


def main():
    print("=" * 70)
    print("ЗАГРУЗКА ЧУКОТКИ ИЗ GADM")
    print("=" * 70)

    with open(GADM_CACHE, 'r', encoding='utf-8') as f:
        gadm = json.load(f)

    chuk_features = []
    for feat in gadm.get('features', []):
        props = feat.get('properties', {})
        if 'Chukot' in props.get('NAME_1', ''):
            chuk_features.append(feat)

    print(f"GADM features: {len(chuk_features)}")

    with engine.begin() as conn:
        rid = conn.execute(text(
            "SELECT id FROM regions WHERE name = :r"
        ), {"r": REGION}).scalar()
        if not rid:
            print(f"Регион '{REGION}' не найден!")
            return
        rid = str(rid)

        db_rows = conn.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": rid}).fetchall()
        db_dict = {row[1]: str(row[0]) for row in db_rows}
        print(f"DB districts: {len(db_dict)}")

        # Группируем GADM features по целевому БД-району (merge)
        merge_map = {}  # db_name -> [geojson_str, ...]
        unmatched = []

        for feat in chuk_features:
            props = feat.get('properties', {})
            name2 = props.get('NAME_2', '')
            nl_name = props.get('NL_NAME_2', '')
            geom = feat.get('geometry')

            db_name = GADM_TO_DB.get(name2)

            if not db_name:
                unmatched.append((name2, nl_name))
                print(f"  {name2:40s} -> ??? ({nl_name})")
                continue

            if db_name not in db_dict:
                print(f"  {name2:40s} -> [!] '{db_name}' не найден в БД")
                continue

            if geom:
                if db_name not in merge_map:
                    merge_map[db_name] = []
                merge_map[db_name].append(json.dumps(geom))
                label = "(merge)" if len(merge_map[db_name]) > 1 else ""
                print(f"  {name2:40s} -> {db_name} {label}")

        if unmatched:
            print(f"\nНе сопоставлено: {len(unmatched)}")
            for n2, nl in unmatched:
                print(f"  {n2} ({nl})")

        missing = [n for n in db_dict if n not in merge_map]
        if missing:
            print(f"\nРайоны без GADM данных:")
            for m in missing:
                print(f"  {m}")

        # Загрузка
        print(f"\n--- Загрузка ---")
        for db_name, geojson_list in merge_map.items():
            d_id = db_dict[db_name]

            conn.execute(text("""
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                WHERE id = :id
            """), {"g": geojson_list[0], "id": d_id})

            for extra_g in geojson_list[1:]:
                conn.execute(text("""
                    UPDATE districts
                    SET geom = ST_Multi(ST_MakeValid(
                        ST_Union(geom, ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                    ))
                    WHERE id = :id
                """), {"g": extra_g, "id": d_id})

            label = f"{len(geojson_list)} GADM merged" if len(geojson_list) > 1 else "1 GADM"
            print(f"  {db_name}: {label}")

        # geom_simplified
        conn.execute(text("""
            UPDATE districts SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
            WHERE region_id = :rid AND geom IS NOT NULL
        """), {"rid": rid})

        # Итоги
        print(f"\n{'='*70}")
        print("ИТОГИ")
        print("=" * 70)
        rows = conn.execute(text("""
            SELECT d.name,
                   ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1) AS area,
                   ST_NumGeometries(d.geom) AS parts,
                   ST_NPoints(d.geom) AS pts
            FROM districts d WHERE d.region_id = :rid ORDER BY d.name
        """), {"rid": rid}).fetchall()

        total = 0.0
        for r in rows:
            area = float(r[1]) if r[1] else 0
            total += area
            parts = r[2] or 0
            pts = r[3] or 0
            flag = ""
            if parts > 1:
                flag = f" [{parts} частей]"
            if pts == 0:
                flag += " [НЕТ ГЕОМЕТРИИ]"
            print(f"  {r[0]:<45s} {area:>10.1f} km2  {pts:>5} pts{flag}")

        print(f"\n  ВСЕГО: {total:.1f} km2")

        # Пересечения
        print("\n--- Пересечения > 0.1 km2 ---")
        overlaps = conn.execute(text("""
            SELECT d1.name, d2.name,
                   ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1)
            FROM districts d1
            JOIN districts d2 ON d1.id < d2.id
            WHERE d1.region_id = :rid AND d2.region_id = :rid
              AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
              AND ST_Intersects(d1.geom, d2.geom)
              AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > 0.1
            ORDER BY 3 DESC LIMIT 15
        """), {"rid": rid}).fetchall()
        if overlaps:
            for o in overlaps:
                print(f"  {o[0]} <-> {o[1]}: {o[2]} km2")
        else:
            print("  Нет!")

    print("\nГотово!")


if __name__ == "__main__":
    main()
