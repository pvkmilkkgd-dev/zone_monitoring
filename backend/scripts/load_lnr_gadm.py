"""
Загрузка геометрии ЛНР из GADM (Ukraine level 2).
Прямой маппинг с учётом объединения старых районов и городов.
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm41_UKR_2.json'
engine = sa.create_engine(settings.DATABASE_URL)

# Маппинг GADM NAME_2 -> название района в БД
# None = пропустить
GADM_TO_DB = {
    # --- МО (районы) ---
    "Antratsytivs'kyi":        "Антрацитовский муниципальный округ",
    "Bilovods'kyi":            "Беловодский муниципальный округ",
    "Bilokurakyns'kyi":        "Белокуракинский муниципальный округ",
    "Krasnodons'kyi":          "Краснодонский муниципальный округ",
    "Kremins'kyi":             "Кременской муниципальный округ",
    "Lutuhyns'kyi":            "Лутугинский муниципальный округ",
    "Markivs'kyi":             "Марковский муниципальный округ",
    "Milovs'kyi":              "Меловский муниципальный округ",
    "Novoaidars'kyi":          "Новоайдарский муниципальный округ",
    "Novopskovs'kyi":          "Новопсковский муниципальный округ",
    "Pereval's'kyi":           "Перевальский муниципальный округ",
    "Popasnians'kyi":          "Перевальский муниципальный округ",  # Попаснянский -> Перевальский
    "Slovianoserbs'kyi":       "Славяносербский муниципальный округ",
    "Stanychno-Luhans'kyi":    "Станично-Луганский муниципальный округ",
    "Starobil's'kyi":          "Старобельский муниципальный округ",
    "Svativs'kyi":             "Сватовский муниципальный округ",
    "Sverdlovs'kyi":           "Свердловский муниципальный округ",
    "Tro\u2039ts'kyi":         "Троицкий муниципальный округ",

    # --- ГО (города -> городские округа) ---
    "Alchevs'ka":              "городской округ г. Алчевск",
    "Briankivs'ka":            "городской округ г. Брянка",
    "Kirovs'ka":               "городской округ г. Кировск",
    "Krasnoluts'ka":           "городской округ г. Красный Луч",
    "Lysychans'ka":            "городской округ г. Лисичанск",
    "Luhans'ka":               "городской округ г. Луганск",
    "Roven'kivs'ka":           "городской округ г. Ровеньки",
    "Rubezhans'ka":            "городской округ г. Рубежное",
    "Sieverodonets'ka":        "городской округ г. Северодонецк",
    "Stakhanivs'ka":           "городской округ г. Стаханов",

    # --- Города без ГО в БД -> вливаем в окружающий МО ---
    "Antratsitivs'ka":         "Антрацитовский муниципальный округ",   # г. Антрацит
    "Krasnodons'ka":           "Краснодонский муниципальный округ",    # г. Краснодон
    "Sverdlovs'ka":            "Свердловский муниципальный округ",     # г. Свердловск

    # --- Не сопоставлено ---
    "n.a.(182)":               "городской округ г. Первомайск",        # предположительно
}


def main():
    print("=" * 70)
    print("ЗАГРУЗКА ЛНР ИЗ GADM")
    print("=" * 70)

    with open(GADM_CACHE, 'r', encoding='utf-8') as f:
        gadm = json.load(f)

    # Filter Luhansk features
    lnr_features = {}
    for feat in gadm.get('features', []):
        props = feat.get('properties', {})
        r1 = props.get('NAME_1', '')
        if 'Luhans' in r1 or 'Lugans' in r1:
            lnr_features[props.get('NAME_2', '')] = feat
    print(f"GADM features: {len(lnr_features)}")

    with engine.begin() as conn:
        region_id = conn.execute(text(
            "SELECT id FROM regions WHERE name ILIKE '%Луганск%'"
        )).scalar()
        print(f"Регион: {region_id}")

        # Get DB districts
        r = conn.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": str(region_id)})
        db_districts = {row[1]: str(row[0]) for row in r.fetchall()}
        print(f"Районов в БД: {len(db_districts)}")

        # Reset geometry
        conn.execute(text(
            "UPDATE districts SET geom = NULL WHERE region_id = :rid"
        ), {"rid": str(region_id)})
        print("Геометрия сброшена.")

        # Build merge map: db_name -> [geojson, ...]
        merge_map = {}
        skipped = []
        unmapped = []

        for gadm_name, feat in lnr_features.items():
            db_name = GADM_TO_DB.get(gadm_name)
            if db_name is None:
                skipped.append(gadm_name)
                continue
            if db_name not in db_districts:
                print(f"  [!] Район не найден в БД: '{db_name}' (от '{gadm_name}')")
                unmapped.append(gadm_name)
                continue
            geom = feat.get('geometry')
            if geom:
                if db_name not in merge_map:
                    merge_map[db_name] = []
                merge_map[db_name].append(json.dumps(geom))

        if skipped:
            print(f"Пропущено: {skipped}")
        if unmapped:
            print(f"Не найдено в БД: {unmapped}")

        # Apply
        print(f"\n--- Загрузка ---")
        for db_name, geojson_list in merge_map.items():
            d_id = db_districts[db_name]
            # First polygon
            conn.execute(text("""
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                WHERE id = :id
            """), {"g": geojson_list[0], "id": d_id})

            # Merge additional polygons
            for extra_g in geojson_list[1:]:
                conn.execute(text("""
                    UPDATE districts
                    SET geom = ST_Multi(ST_MakeValid(
                        ST_Union(geom, ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                    ))
                    WHERE id = :id
                """), {"g": extra_g, "id": d_id})

            count = len(geojson_list)
            label = f"{count} GADM merged" if count > 1 else "1 GADM"
            print(f"  {db_name}: {label}")

        # Check missing
        missing = [n for n in db_districts if n not in merge_map]
        if missing:
            print(f"\n  [!] Без геометрии: {missing}")

        # Final stats
        print(f"\n{'='*70}")
        print("ИТОГО")
        print("=" * 70)
        r = conn.execute(text("""
            SELECT d.name,
                   ST_NPoints(d.geom) as pts,
                   ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1) as area,
                   ST_NumGeometries(d.geom) as parts
            FROM districts d WHERE d.region_id = :rid ORDER BY d.name
        """), {"rid": str(region_id)})
        total = 0.0
        for row in r:
            pts = row[1] or 0
            area = float(row[2]) if row[2] else 0
            total += area
            parts = row[3] or 0
            flag = " [!!! НЕТ ГЕОМЕТРИИ]" if pts == 0 else ""
            if parts > 1:
                flag += f" [{parts} частей]"
            print(f"  {row[0]:<55} {pts:>6} pts {area:>8.1f} km²{flag}")
        print(f"\n  ОБЩАЯ ПЛОЩАДЬ: {total:.1f} km²")

        # Check overlaps
        print("\n--- Пересечения ---")
        r = conn.execute(text("""
            SELECT d1.name, d2.name,
                   ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1)
            FROM districts d1
            JOIN districts d2 ON d1.id < d2.id
            WHERE d1.region_id = :rid AND d2.region_id = :rid
              AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
              AND ST_Intersects(d1.geom, d2.geom)
              AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > 0.1
            ORDER BY 3 DESC LIMIT 15
        """), {"rid": str(region_id)})
        overlaps = r.fetchall()
        if overlaps:
            for o in overlaps:
                print(f"  {o[0]} <-> {o[1]}: {o[2]} km²")
        else:
            print("  Пересечений нет!")

    print("\nГотово!")


if __name__ == "__main__":
    main()
