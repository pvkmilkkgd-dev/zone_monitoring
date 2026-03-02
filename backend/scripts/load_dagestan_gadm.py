# -*- coding: utf-8 -*-
"""
Загрузка геометрии районов Республики Дагестан из GADM Russia level 2.
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm_russia_level2.json'
REGION = 'Республика Дагестан'

# Ручной маппинг GADM NAME_2 -> название в БД (для сложных случаев)
MANUAL_MAP = {
    "Makhachkalagorsovet": "городской округ г. Махачкала",
    "Kizilyurtovskiy/Dokuzparinskiyr": "Кизилюртовский муниципальный район",
    "DagestanskieOg": "городской округ г. Дагестанские Огни",
}

engine = create_engine(settings.DATABASE_URL)


def normalize(s):
    """Убрать пробелы, дефисы, привести к нижнему регистру."""
    return s.lower().replace(' ', '').replace('-', '').replace('ё', 'е')


def match_gadm_to_db(nl_name, name2, db_names):
    """Сопоставить GADM запись с названием из БД."""
    # 1. Ручной маппинг
    if name2 in MANUAL_MAP:
        return MANUAL_MAP[name2]

    # 2. NL_NAME_2 содержит русское название — парсим
    if nl_name:
        nl_clean = nl_name.strip()

        # "Xxxрайон" → ищем "Xxx муниципальный район" или "Xxxский муниципальный район"
        if nl_clean.endswith('район'):
            base = nl_clean.replace('район', '').strip()
            for db_name in db_names:
                if 'муниципальный район' in db_name:
                    db_base = db_name.replace(' муниципальный район', '')
                    if normalize(db_base) == normalize(base):
                        return db_name

        # Город без "район" → "городской округ г. Xxx"
        for db_name in db_names:
            if db_name.startswith('городской округ г. '):
                city = db_name.replace('городской округ г. ', '')
                # "Буйнакск" == "Буйнакск", "Махачкала(горсовет)" содержит "Махачкала"
                if normalize(city) == normalize(nl_clean):
                    return db_name
                if normalize(city) in normalize(nl_clean) or normalize(nl_clean) in normalize(city):
                    return db_name

    # 3. По NAME_2 (английское) — fallback
    for db_name in db_names:
        db_norm = normalize(db_name)
        n2_norm = normalize(name2)
        if n2_norm[:6] == db_norm[:6]:
            return db_name

    return None


def main():
    print("=" * 70)
    print("ЗАГРУЗКА ДАГЕСТАНА ИЗ GADM")
    print("=" * 70)

    with open(GADM_CACHE, 'r', encoding='utf-8') as f:
        gadm = json.load(f)

    dag_features = []
    for feat in gadm.get('features', []):
        props = feat.get('properties', {})
        if 'Dagestan' in props.get('NAME_1', ''):
            dag_features.append(feat)

    print(f"GADM features: {len(dag_features)}")

    with engine.begin() as conn:
        rid = str(conn.execute(text(
            "SELECT id FROM regions WHERE name = :r"
        ), {"r": REGION}).scalar())

        db_rows = conn.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": rid}).fetchall()
        db_dict = {row[1]: str(row[0]) for row in db_rows}
        db_names = list(db_dict.keys())
        print(f"DB districts: {len(db_names)}")

        # Маппинг
        matched = {}  # db_name -> [geojson, ...]
        unmatched = []

        for feat in dag_features:
            props = feat.get('properties', {})
            name2 = props.get('NAME_2', '')
            nl_name = props.get('NL_NAME_2', '')
            geom = feat.get('geometry')

            db_name = match_gadm_to_db(nl_name, name2, db_names)

            if db_name and geom:
                if db_name not in matched:
                    matched[db_name] = []
                matched[db_name].append(json.dumps(geom))
                print(f"  {name2:45s} -> {db_name}")
            else:
                unmatched.append((name2, nl_name))
                print(f"  {name2:45s} -> ??? (NL: {nl_name})")

        if unmatched:
            print(f"\nНе сопоставлено: {len(unmatched)}")
            for n2, nl in unmatched:
                print(f"  {n2} ({nl})")
            return

        missing = [n for n in db_names if n not in matched]
        if missing:
            print(f"\nРайоны без GADM данных: {len(missing)}")
            for m in missing:
                print(f"  {m}")

        # Загрузка
        print(f"\n--- Загрузка геометрии ---")
        for db_name, geojson_list in matched.items():
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

            label = f"{len(geojson_list)} merged" if len(geojson_list) > 1 else "OK"
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
        multi = 0
        for r in rows:
            area = float(r[1]) if r[1] else 0
            total += area
            parts = r[2] or 0
            pts = r[3] or 0
            flag = ""
            if parts > 1:
                flag = f" [{parts} частей]"
                multi += 1
            if pts == 0:
                flag += " [НЕТ ГЕОМЕТРИИ]"
            print(f"  {r[0]:<50s} {area:>8.1f} km2  {pts:>5} pts{flag}")

        print(f"\n  ВСЕГО: {total:.1f} km2")
        print(f"  Районов с >1 частью: {multi}")

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
            ORDER BY 3 DESC LIMIT 20
        """), {"rid": rid}).fetchall()
        if overlaps:
            for o in overlaps:
                print(f"  {o[0]} <-> {o[1]}: {o[2]} km2")
        else:
            print("  Нет!")

    print("\nГотово!")


if __name__ == "__main__":
    main()
