# -*- coding: utf-8 -*-
"""
Шаг 2 отката: перезагрузить Махачкалу из Overpass и вырезать пересечения.
Тарумовский уже восстановлен.
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
    urls = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    for attempt in range(3):
        for url in urls:
            try:
                data = urllib.parse.urlencode({"data": q}).encode()
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "ZoneMonitoring/1.0"})
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return json.loads(resp.read().decode())
            except Exception as e:
                print(f"  attempt {attempt+1} {url}: {e}")
        if attempt < 2:
            print(f"  Waiting 10s before retry...")
            time.sleep(10)
    raise RuntimeError("Overpass failed after 3 attempts")

def nominatim_lookup(osm_id):
    url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json&polygon_geojson=1"
    req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        return data[0] if data else None

print("=== Reloading Makhachkala ===")
q = '[out:json][timeout:60];area["ISO3166-2"="RU-DA"]->.d;(relation["boundary"="administrative"]["admin_level"="6"](area.d););out tags;'
result = overpass_query(q)

osm_ids = []
for el in result.get("elements", []):
    n = (el.get("tags", {}).get("name") or "").lower()
    if "махачкала" in n:
        osm_ids.append(el["id"])
        print(f"  Found R{el['id']}: {el.get('tags', {}).get('name')}")

if not osm_ids:
    print("NOT FOUND")
    sys.exit(1)

best_geojson = None
best_area = 0
for oid in osm_ids:
    print(f"  Fetching R{oid}...")
    time.sleep(1.5)
    d = nominatim_lookup(oid)
    if not d or not d.get("geojson"):
        print(f"    no geometry")
        continue
    gj = d["geojson"]
    if gj.get("type") not in ("Polygon", "MultiPolygon"):
        print(f"    type={gj.get('type')}")
        continue
    sz = len(json.dumps(gj))
    print(f"    type={gj['type']}, size={sz}")
    if sz > best_area:
        best_area = sz
        best_geojson = gj

if not best_geojson:
    print("No valid geometry")
    sys.exit(1)

with engine.begin() as conn:
    rid = str(conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())
    mid = str(conn.execute(text(
        "SELECT id FROM districts WHERE region_id = :rid AND name = :n"
    ), {"rid": rid, "n": "городской округ г. Махачкала"}).scalar())

    # Загружаем оригинальную геометрию
    conn.execute(text("""
        UPDATE districts SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
        WHERE id = :mid
    """), {"g": json.dumps(best_geojson), "mid": mid})

    a = conn.execute(text(
        "SELECT ROUND((ST_Area(geom::geography)/1e6)::numeric, 1) FROM districts WHERE id = :mid"
    ), {"mid": mid}).scalar()
    print(f"  Loaded from Overpass: {a} km2")

    # Вырезаем пересечения со всеми другими районами
    print("\n=== Cutting overlaps ===")
    conn.execute(text("""
        UPDATE districts SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(
            ST_Difference(
                geom,
                (SELECT ST_Union(d2.geom) FROM districts d2 WHERE d2.region_id = :rid AND d2.id != :mid AND d2.geom IS NOT NULL)
            )
        ), 3))
        WHERE id = :mid
    """), {"rid": rid, "mid": mid})

    result = conn.execute(text("""
        SELECT ROUND((ST_Area(geom::geography)/1e6)::numeric, 1),
               ST_NumGeometries(geom)
        FROM districts WHERE id = :mid
    """), {"mid": mid}).fetchone()
    print(f"  After cutting: {result[0]} km2, {result[1]} parts")

    # Обновляем geom_simplified
    conn.execute(text("""
        UPDATE districts SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
        WHERE region_id = :rid AND geom IS NOT NULL
    """), {"rid": rid})

print("\n=== Verification ===")
with engine.connect() as conn:
    multi = conn.execute(text("""
        SELECT d.name, ST_NumGeometries(d.geom), ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.geom IS NOT NULL AND ST_NumGeometries(d.geom) > 1
    """), {"region": REGION}).fetchall()
    if multi:
        for m in multi:
            print(f"  {m[0]}: {m[1]} parts, {m[2]} km2")
    else:
        print("  All districts have 1 part!")

    makh = conn.execute(text("""
        SELECT ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = 'городской округ г. Махачкала'
    """), {"region": REGION}).scalar()
    print(f"\n  Makhachkala final: {makh} km2")
