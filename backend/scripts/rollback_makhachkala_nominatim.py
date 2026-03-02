# -*- coding: utf-8 -*-
"""
Перезагрузить Махачкалу напрямую через Nominatim (без Overpass).
OSM relation ID для ГО Махачкала: 1861406
"""
import sys
import io
import json
import urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

REGION = "Республика Дагестан"
OSM_ID = 1963798
engine = create_engine(settings.DATABASE_URL)

def nominatim_lookup(osm_id):
    url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json&polygon_geojson=1"
    req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
        return data[0] if data else None

print(f"Fetching R{OSM_ID} from Nominatim...")
d = nominatim_lookup(OSM_ID)
if not d or not d.get("geojson"):
    print("No geometry!")
    sys.exit(1)

gj = d["geojson"]
print(f"  type={gj['type']}")

with engine.begin() as conn:
    rid = str(conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())
    mid = str(conn.execute(text(
        "SELECT id FROM districts WHERE region_id = :rid AND name = :n"
    ), {"rid": rid, "n": "городской округ г. Махачкала"}).scalar())

    conn.execute(text("""
        UPDATE districts SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
        WHERE id = :mid
    """), {"g": json.dumps(gj), "mid": mid})

    a = conn.execute(text(
        "SELECT ROUND((ST_Area(geom::geography)/1e6)::numeric, 1) FROM districts WHERE id = :mid"
    ), {"mid": mid}).scalar()
    print(f"  Loaded: {a} km2")

    # Вырезаем пересечения со всеми другими районами
    print("Cutting overlaps with neighbors...")
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

    # geom_simplified
    conn.execute(text("""
        UPDATE districts SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
        WHERE region_id = :rid AND geom IS NOT NULL
    """), {"rid": rid})

print("\nVerification:")
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
    print(f"  Makhachkala: {makh} km2")
