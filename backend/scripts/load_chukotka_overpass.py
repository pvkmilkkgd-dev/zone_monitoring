# -*- coding: utf-8 -*-
"""
Загрузить геометрию Чукотского АО из OpenStreetMap (Overpass + Nominatim).
ISO3166-2: RU-CHU
"""
import sys, io, json, time
import urllib.request, urllib.parse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

REGION = "Чукотский автономный округ"
engine = create_engine(settings.DATABASE_URL)


def overpass_query(q):
    for url in [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]:
        try:
            data = urllib.parse.urlencode({"data": q}).encode()
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "ZoneMonitoring/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"  {url}: {e}")
    raise RuntimeError("Overpass failed")


def nominatim_lookup(osm_id):
    url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json&polygon_geojson=1"
    req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
        return data[0] if data else None


def normalize(name):
    n = (name or "").lower().strip()
    for w in ["муниципальный район", "муниципальный округ", "городской округ",
              "район", "округ", "город", "г.", "с п"]:
        n = n.replace(w, "")
    n = n.replace("-", " ").replace("ё", "е").strip()
    while "  " in n:
        n = n.replace("  ", " ")
    return n


def match_osm_to_db(osm_name, db_names):
    osm_norm = normalize(osm_name)
    for db_name in db_names:
        if normalize(db_name) == osm_norm:
            return db_name
    for db_name in db_names:
        db_norm = normalize(db_name)
        if osm_norm and db_norm and (osm_norm in db_norm or db_norm in osm_norm):
            return db_name
    osm_first = (osm_norm.split() or [""])[0]
    if len(osm_first) > 2:
        for db_name in db_names:
            db_first = (normalize(db_name).split() or [""])[0]
            if osm_first == db_first:
                return db_name
    return None


def main():
    print("=" * 70)
    print("ЗАГРУЗКА ЧУКОТКИ ИЗ OSM (Overpass + Nominatim)")
    print("=" * 70)

    # 1. Получить список районов из Overpass
    print("\n1) Overpass: admin_level=6 в Чукотском АО")
    query = """
    [out:json][timeout:60];
    area["ISO3166-2"="RU-CHU"]->.chu;
    ( relation["boundary"="administrative"]["admin_level"="6"](area.chu); );
    out tags;
    """
    result = overpass_query(query)
    elements = result.get("elements", [])
    print(f"   Найдено {len(elements)} relations")
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "?")
        print(f"   R{el['id']}: {name}")

    # 2. Сопоставить с БД
    with engine.connect() as conn:
        db_rows = conn.execute(text("""
            SELECT d.name FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region ORDER BY d.name
        """), {"region": REGION}).fetchall()
    db_names = [r[0] for r in db_rows]
    print(f"\n   БД районов: {len(db_names)}")

    used_db = set()
    mapping = {}  # osm_id -> (db_name, osm_name)

    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:ru") or ""
        available = [n for n in db_names if n not in used_db]
        db_match = match_osm_to_db(name, available)
        if db_match:
            mapping[el["id"]] = (db_match, name)
            used_db.add(db_match)
            print(f"   R{el['id']}: {name} -> {db_match}")
        else:
            print(f"   R{el['id']}: {name} -> ??? НЕ НАЙДЕН")

    not_matched = [n for n in db_names if n not in used_db]
    if not_matched:
        print(f"\n   Без пары в OSM:")
        for n in not_matched:
            print(f"     {n}")

    print(f"\n   Сопоставлено: {len(mapping)} из {len(db_names)}")

    # 3. Загрузить геометрии через Nominatim
    print("\n2) Загрузка геометрий из Nominatim")
    loaded = 0
    with engine.begin() as conn:
        for osm_id, (db_name, osm_name) in mapping.items():
            time.sleep(1.2)
            try:
                data = nominatim_lookup(osm_id)
            except Exception as e:
                print(f"   FAIL R{osm_id} ({db_name}): {e}")
                continue
            if not data or not data.get("geojson"):
                print(f"   SKIP R{osm_id} ({db_name}): no geom")
                continue
            geojson = data["geojson"]
            if geojson.get("type") not in ("Polygon", "MultiPolygon"):
                print(f"   SKIP R{osm_id} ({db_name}): type={geojson.get('type')}")
                continue

            conn.execute(text("""
                UPDATE districts d
                SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)))
                FROM regions r
                WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
            """), {"gj": json.dumps(geojson), "region": REGION, "name": db_name})
            loaded += 1
            print(f"   R{osm_id}: {db_name} OK")

        # geom_simplified
        rid = str(conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())
        conn.execute(text("""
            UPDATE districts SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
            WHERE region_id = :rid AND geom IS NOT NULL
        """), {"rid": rid})

    print(f"\n   Загружено: {loaded}")

    # 4. Итоги
    print(f"\n{'='*70}")
    print("ИТОГИ")
    print("=" * 70)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT d.name,
                   ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1) AS area,
                   ST_NumGeometries(d.geom) AS parts,
                   ST_NPoints(d.geom) AS pts
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.geom IS NOT NULL
            ORDER BY d.name
        """), {"region": REGION}).fetchall()

        total = 0.0
        for r in rows:
            area = float(r[1]) if r[1] else 0
            total += area
            parts = r[2] or 0
            pts = r[3] or 0
            flag = f" [{parts} частей]" if parts > 1 else ""
            print(f"  {r[0]:<45s} {area:>10.1f} km2  {pts:>6} pts{flag}")

        print(f"\n  ВСЕГО: {total:.1f} km2")

        overlaps = conn.execute(text("""
            SELECT d1.name, d2.name,
                   ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6)::numeric, 1)
            FROM districts d1
            JOIN districts d2 ON d1.id < d2.id
            WHERE d1.region_id = (SELECT id FROM regions WHERE name = :region)
              AND d2.region_id = d1.region_id
              AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
              AND ST_Intersects(d1.geom, d2.geom)
              AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > 0.1
            ORDER BY 3 DESC LIMIT 15
        """), {"region": REGION}).fetchall()
        print("\n--- Пересечения > 0.1 km2 ---")
        if overlaps:
            for o in overlaps:
                print(f"  {o[0]} <-> {o[1]}: {o[2]} km2")
        else:
            print("  Нет!")

    print("\nГотово!")


if __name__ == "__main__":
    main()
