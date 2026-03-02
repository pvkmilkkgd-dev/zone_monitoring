"""
Загрузка геометрии Запорожской области из GADM (Ukraine level 2).
Прямой маппинг GADM -> БД с учётом украинских/российских названий.
"""
import sys
import io
import json
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm41_UKR_2.json'
GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_UKR_2.json"

engine = sa.create_engine(settings.DATABASE_URL)

# Прямой маппинг: GADM NAME_2 -> список подстрок названий районов в БД
# Для МО: объединяем несколько старых районов в один
# Для ГО: берём "ка" (городскую общину)
GADM_TO_DB = {
    # Городские округа (берём "ка" = городская община)
    "Berdians'ka": "городской округ г. Бердянск",
    "Melitopol's'ka": "городской округ г. Мелитополь",
    "Enerhodars'ka": "городской округ г. Энергодар",
    # GADM города-районы (берём "кий" = район)
    "Zaporiz'ka": None,  # пропускаем - это ГО Запорожье, которого нет в ДНР-структуре
    "Tokmats'ka": None,  # пропускаем - дубль города Токмак

    # Муниципальные округа (объединяем из GADM районов)
    "Iakymivs'kyi": "Акимовский муниципальный округ",
    "Vasylivs'kyi": "Васильевский муниципальный округ",
    "Veselivs'kyi": "Веселовский муниципальный округ",
    "Kamians'ko-Dniprovs'kyi": "Каменско-Днепровский муниципальный округ",
    "Kuibyshevs'kyi": "Куйбышевский муниципальный округ",
    "Mykhailivs'kyi": "Михайловский муниципальный округ",
    "Polohivs'kyi": "Пологовский муниципальный округ",
    "Pryazovs'kyi": "Приазовский муниципальный округ",
    "Prymors'kyi": "Приморский муниципальный округ",
    "Tokmats'kyi": "Токмакский муниципальный округ",
    "Chernihivs'kyi": "Черниговский муниципальный округ",

    # Дополнительные GADM районы -> объединяем в существующие МО
    # Эти районы были объединены в более крупные МО
    "Berdians'kyi": "Приморский муниципальный округ",      # Бердянский район -> Приморский МО
    "Melitopol's'kyi": "Веселовский муниципальный округ",   # Мелитопольский район -> может быть часть
    "Orikhivs'kyi": "Пологовский муниципальный округ",      # Ореховский район -> Пологовский МО
    "Huliaipil's'kyi": "Пологовский муниципальный округ",   # Гуляйпольский район -> Пологовский МО
    "Rozivs'kyi": "Куйбышевский муниципальный округ",       # Розовский район -> Куйбышевский МО
    "Novomykola\u2039vs'kyi": "Михайловский муниципальный округ", # Новониколаевский -> Михайловский МО
    "Velykobilozers'kyi": "Васильевский муниципальный округ", # Великобелозерский -> Васильевский МО
    "Vil'nians'kyi": "Васильевский муниципальный округ",     # Вольнянский -> Васильевский МО
    "Zaporiz'kyi": "Васильевский муниципальный округ",       # Запорожский район -> Васильевский МО
}


def download_gadm():
    os.makedirs(os.path.dirname(GADM_CACHE), exist_ok=True)
    if os.path.exists(GADM_CACHE):
        print("Загрузка из кэша GADM UKR...")
        with open(GADM_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    print("Скачивание GADM Ukraine level 2...")
    import urllib.request
    req = urllib.request.Request(GADM_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    with open(GADM_CACHE, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    print(f"Кэшировано {len(data.get('features', []))} features")
    return data


def main():
    print("=" * 70)
    print("ЗАГРУЗКА ЗАПОРОЖСКОЙ ОБЛАСТИ ИЗ GADM")
    print("=" * 70)

    gadm = download_gadm()
    if not gadm:
        return

    # Filter Zaporizhzhia features
    zap_features = {}
    for f in gadm.get('features', []):
        props = f.get('properties', {})
        r1 = props.get('NAME_1', '')
        if 'Zaporiz' in r1:
            name2 = props.get('NAME_2', '')
            zap_features[name2] = f

    print(f"GADM features: {len(zap_features)}")

    with engine.begin() as conn:
        # Get region ID
        r = conn.execute(text("SELECT id FROM regions WHERE name ILIKE '%Запорож%'"))
        region = r.fetchone()
        if not region:
            print("Регион не найден!")
            return
        region_id = str(region[0])

        # Get DB districts
        r = conn.execute(text("""
            SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name
        """), {"rid": region_id})
        db_districts = {row[1]: str(row[0]) for row in r.fetchall()}
        print(f"Районов в БД: {len(db_districts)}")

        # Сброс геометрии (начинаем с чистого листа для Запорожской обл.)
        conn.execute(text("""
            UPDATE districts SET geom = NULL WHERE region_id = :rid
        """), {"rid": region_id})

        # Маппинг: db_name -> [list of GADM geometries to union]
        merge_map = {}  # db_name -> [geojson_geom, ...]
        skipped = []
        unmapped = []

        for gadm_name, gadm_feature in zap_features.items():
            db_name = GADM_TO_DB.get(gadm_name)
            if db_name is None:
                skipped.append(gadm_name)
                continue
            if db_name not in db_districts:
                print(f"  [!] DB район не найден: '{db_name}' (от GADM '{gadm_name}')")
                unmapped.append(gadm_name)
                continue

            geom = gadm_feature.get('geometry')
            if geom:
                if db_name not in merge_map:
                    merge_map[db_name] = []
                merge_map[db_name].append(json.dumps(geom))

        print(f"\nПропущено GADM: {skipped}")
        if unmapped:
            print(f"Не найдено в БД: {unmapped}")

        # Apply geometries
        print(f"\n--- Загрузка геометрии ---")
        loaded = 0
        for db_name, geojson_list in merge_map.items():
            d_id = db_districts[db_name]

            if len(geojson_list) == 1:
                # Один GADM район -> один DB район
                conn.execute(text("""
                    UPDATE districts
                    SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                    WHERE id = :id
                """), {"g": geojson_list[0], "id": d_id})
                print(f"  {db_name}: 1 GADM polygon")
            else:
                # Несколько GADM районов -> объединяем через ST_Union
                # Сначала загружаем первый
                conn.execute(text("""
                    UPDATE districts
                    SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                    WHERE id = :id
                """), {"g": geojson_list[0], "id": d_id})
                # Затем объединяем остальные
                for extra_g in geojson_list[1:]:
                    conn.execute(text("""
                        UPDATE districts
                        SET geom = ST_Multi(ST_MakeValid(
                            ST_Union(
                                geom,
                                ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))
                            )
                        ))
                        WHERE id = :id
                    """), {"g": extra_g, "id": d_id})
                print(f"  {db_name}: {len(geojson_list)} GADM polygons merged")

            loaded += 1

        # Check for districts without geometry
        missing_geom = []
        for db_name, d_id in db_districts.items():
            if db_name not in merge_map:
                missing_geom.append(db_name)

        if missing_geom:
            print(f"\n  [!] Без геометрии: {missing_geom}")

        # Final stats
        print(f"\n{'='*70}")
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 70)
        r = conn.execute(text("""
            SELECT d.name,
                   ST_NPoints(d.geom) as pts,
                   ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1) as area,
                   ST_NumGeometries(d.geom) as parts
            FROM districts d
            WHERE d.region_id = :rid
            ORDER BY d.name
        """), {"rid": region_id})
        total_area = 0.0
        for row in r:
            pts = row[1] or 0
            area = float(row[2]) if row[2] else 0
            parts = row[3] or 0
            total_area += area
            flag = " [!!! НЕТ ГЕОМЕТРИИ]" if pts == 0 else ""
            if parts > 1:
                flag += f" [{parts} частей]"
            print(f"  {row[0]:<50} {pts:>6} pts  {area:>8.1f} km²{flag}")
        print(f"\n  ИТОГО: {total_area:.1f} km²")

        # Check overlaps
        print("\n--- Проверка пересечений ---")
        r = conn.execute(text("""
            SELECT d1.name, d2.name,
                   ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1)
            FROM districts d1
            JOIN districts d2 ON d1.id < d2.id
            WHERE d1.region_id = :rid AND d2.region_id = :rid
              AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
              AND ST_Overlaps(d1.geom, d2.geom)
              AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > 0.1
            ORDER BY 3 DESC LIMIT 10
        """), {"rid": region_id})
        overlaps = r.fetchall()
        if overlaps:
            for o in overlaps:
                print(f"  {o[0]} <-> {o[1]}: {o[2]} km²")
        else:
            print("  Пересечений нет!")

        print("\nГотово!")


if __name__ == "__main__":
    main()
