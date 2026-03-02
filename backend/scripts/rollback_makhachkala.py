# -*- coding: utf-8 -*-
"""
Откат последнего изменения Махачкалы.
1. Перезагрузить Тарумовский из Overpass + применить фиксы (щель + дыра)
2. Перезагрузить Махачкалу из Overpass
3. Вырезать из Махачкалы пересечения со всеми соседями
4. Обновить geom_simplified
"""
import sys
import io
import json
import time
import urllib.request
import urllib.parse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

REGION = "Республика Дагестан"
engine = create_engine(settings.DATABASE_URL)

def overpass_query(q):
    for url in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        return data[0] if data else None

def reload_district(conn, name, keyword):
    """Перезагрузить район из Overpass по ключевому слову."""
    print(f"\n=== Reloading {name} ===")
    q = '[out:json][timeout:60];area["ISO3166-2"="RU-DA"]->.d;(relation["boundary"="administrative"]["admin_level"="6"](area.d););out tags;'
    result = overpass_query(q)

    osm_ids = []
    for el in result.get("elements", []):
        n = (el.get("tags", {}).get("name") or "").lower()
        if keyword in n:
            osm_ids.append(el["id"])

    if not osm_ids:
        print(f"  NOT FOUND for '{keyword}'")
        return False

    best_geojson = None
    best_area = 0

    for oid in osm_ids:
        print(f"  Trying R{oid}...")
        time.sleep(1.1)
        d = nominatim_lookup(oid)
        if not d or not d.get("geojson"):
            continue
        gj = d["geojson"]
        if gj.get("type") not in ("Polygon", "MultiPolygon"):
            continue

        # Выбираем самый большой по bbox
        coords = json.dumps(gj)
        area_est = len(coords)
        if area_est > best_area:
            best_area = area_est
            best_geojson = gj

    if not best_geojson:
        print(f"  No valid geometry for '{name}'")
        return False

    conn.execute(text("""
        UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
        FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
    """), {"g": json.dumps(best_geojson), "region": REGION, "name": name})

    a = conn.execute(text("""
        SELECT ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = :name
    """), {"region": REGION, "name": name}).scalar()
    print(f"  Loaded: {a} km2")
    return True


with engine.begin() as conn:
    rid = str(conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())

    # === 1. Перезагрузить Тарумовский ===
    ok = reload_district(conn, "Тарумовский муниципальный район", "тарумов")
    if not ok:
        print("FAILED to reload Tarumovsky")
        sys.exit(1)

    # Фикс щели (buffer +50/-50)
    print("  Fixing slit...")
    conn.execute(text("""
        UPDATE districts d SET geom = ST_Multi(ST_MakeValid(
            ST_Buffer(ST_Buffer(d.geom::geography, 50)::geography, -50)::geometry
        ))
        FROM regions r
        WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
    """), {"region": REGION, "name": "Тарумовский муниципальный район"})

    # Заполнить дыру (убираем interior rings)
    print("  Filling holes...")
    conn.execute(text("""
        UPDATE districts d SET geom = sub.geom
        FROM (
            SELECT d.id,
                   ST_Multi(ST_Union(ST_MakePolygon(ST_ExteriorRing((dump).geom)))) AS geom
            FROM districts d
            JOIN regions r ON d.region_id = r.id,
            LATERAL ST_Dump(d.geom) AS dump
            WHERE r.name = :region AND d.name = :name
            GROUP BY d.id
        ) sub
        WHERE d.id = sub.id
    """), {"region": REGION, "name": "Тарумовский муниципальный район"})

    a = conn.execute(text("""
        SELECT ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = :name
    """), {"region": REGION, "name": "Тарумовский муниципальный район"}).scalar()
    print(f"  Tarumovsky after fixes: {a} km2")

    time.sleep(1.1)

    # === 2. Перезагрузить Махачкалу ===
    ok = reload_district(conn, "городской округ г. Махачкала", "махачкала")
    if not ok:
        print("FAILED to reload Makhachkala")
        sys.exit(1)

    a_before = conn.execute(text("""
        SELECT ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = :name
    """), {"region": REGION, "name": "городской округ г. Махачкала"}).scalar()
    print(f"  Makhachkala from Overpass: {a_before} km2")

    # === 3. Вырезать из Махачкалы пересечения со ВСЕМИ другими районами ===
    print("\n=== Cutting overlaps from Makhachkala ===")
    mid = str(conn.execute(text(
        "SELECT id FROM districts WHERE region_id = :rid AND name = :n"
    ), {"rid": rid, "n": "городской округ г. Махачкала"}).scalar())

    # Объединение всех остальных районов
    conn.execute(text("""
        UPDATE districts SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(
            ST_Difference(
                geom,
                (SELECT ST_Union(d2.geom) FROM districts d2 WHERE d2.region_id = :rid AND d2.id != :mid AND d2.geom IS NOT NULL)
            )
        ), 3))
        WHERE id = :mid
    """), {"rid": rid, "mid": mid})

    a_after = conn.execute(text("""
        SELECT ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1),
               ST_NumGeometries(d.geom)
        FROM districts d WHERE d.id = :mid
    """), {"mid": mid}).fetchone()
    print(f"  Makhachkala after cutting overlaps: {a_after[0]} km2, {a_after[1]} parts")

    # === 4. Обновить geom_simplified для всех ===
    conn.execute(text("""
        UPDATE districts SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
        WHERE region_id = :rid AND geom IS NOT NULL
    """), {"rid": rid})

print("\n=== Verification ===")
with engine.connect() as conn:
    multi = conn.execute(text("""
        SELECT d.name, ST_NumGeometries(d.geom),
               ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.geom IS NOT NULL
        ORDER BY d.name
    """), {"region": REGION}).fetchall()
    multi_count = 0
    for m in multi:
        if m[1] > 1:
            multi_count += 1
            print(f"  {m[0]}: {m[1]} parts, {m[2]} km2")
    if multi_count == 0:
        print("  All districts have 1 part!")
    else:
        print(f"  {multi_count} districts with >1 part")
