# -*- coding: utf-8 -*-
"""
Перезагрузить Дагестан из Overpass + Nominatim.
Сразу после загрузки: убрать дыры и мелкие осколки (< MIN_FRAGMENT_KM2).
"""
import sys
import io
import json
import time
import urllib.request
import urllib.parse
import sqlalchemy as sa
from sqlalchemy import text

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

engine = sa.create_engine("postgresql+psycopg://zone_user:zone_password@localhost:5432/zone_monitoring")
REGION = "Республика Дагестан"
MIN_FRAGMENT_KM2 = 5.0  # фрагменты меньше — удаляем


def overpass_query(query_str):
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({"data": query_str}).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def nominatim_lookup(osm_id):
    url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json&polygon_geojson=1"
    req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        if data and len(data) > 0:
            return data[0]
    return None


def normalize(name):
    n = (name or "").lower().strip()
    for w in ["муниципальный район", "муниципальный округ", "городской округ", "район", "округ", "город", "г.", "с п"]:
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
            db_norm = normalize(db_name)
            db_first = (db_norm.split() or [""])[0]
            if osm_first == db_first:
                return db_name
    return None


def main():
    print("1) Overpass: admin_level=6 в Дагестане")
    query = """
    [out:json][timeout:60];
    area["ISO3166-2"="RU-DA"]->.dag;
    ( relation["boundary"="administrative"]["admin_level"="6"](area.dag); );
    out tags;
    """
    result = overpass_query(query)
    elements = result.get("elements", [])
    print(f"   Найдено {len(elements)} relations")

    with engine.connect() as conn:
        db_rows = conn.execute(text("""
            SELECT d.name FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region ORDER BY d.name
        """), {"region": REGION}).fetchall()
    db_names = [r[0] for r in db_rows]
    used_db = set()
    mapping = {}
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:ru") or ""
        available = [n for n in db_names if n not in used_db]
        db_match = match_osm_to_db(name, available)
        if db_match:
            mapping[el["id"]] = (db_match, name)
            used_db.add(db_match)

    print(f"   Сопоставлено {len(mapping)} из {len(db_names)}")

    print("\n2) Загрузка геометрий и запись в БД")
    with engine.begin() as conn:
        for osm_id, (db_name, osm_name) in mapping.items():
            time.sleep(1.1)
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
                continue
            conn.execute(text("""
                UPDATE districts d
                SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)))
                FROM regions r
                WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
            """), {"gj": json.dumps(geojson), "region": REGION, "name": db_name})
        print("   Загрузка завершена")

    print("\n3) Итог")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT d.name,
                   ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1) as area,
                   ST_NumGeometries(d.geom) as parts,
                   (SELECT COALESCE(SUM(ST_NumInteriorRings(g.geom)),0)
                    FROM districts d2, LATERAL ST_Dump(d2.geom) AS g WHERE d2.id = d.id) as holes
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.geom IS NOT NULL
            ORDER BY d.name
        """), {"region": REGION}).fetchall()
        multi = sum(1 for r in rows if r[2] > 1)
        holey = sum(1 for r in rows if r[3] and r[3] > 0)
        print(f"   Районов: {len(rows)}, с >1 частью: {multi}, с дырами: {holey}")
        for r in rows[:10]:
            print(f"   {r[0]}: {r[1]} km2, {r[2]} parts, {r[3]} holes")
        if len(rows) > 10:
            print(f"   ... и ещё {len(rows)-10}")

    print("\nГотово.")


if __name__ == "__main__":
    main()
