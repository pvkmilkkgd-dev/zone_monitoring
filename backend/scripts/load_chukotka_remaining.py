# -*- coding: utf-8 -*-
"""Дозагрузить Провиденский и Чукотский из Nominatim."""
import sys, io, json, time, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

REGION = "Чукотский автономный округ"
engine = create_engine(settings.DATABASE_URL)

TO_LOAD = [
    (1949882, "Провиденский муниципальный округ"),
    (1949884, "Чукотский муниципальный район"),
]

def nominatim_lookup(osm_id):
    url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json&polygon_geojson=1"
    req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
        return data[0] if data else None

with engine.begin() as conn:
    rid = str(conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())
    for osm_id, db_name in TO_LOAD:
        print(f"Loading R{osm_id} ({db_name})...")
        try:
            data = nominatim_lookup(osm_id)
        except Exception as e:
            print(f"  FAIL: {e}")
            continue
        if not data or not data.get("geojson"):
            print("  no geom")
            continue
        gj = data["geojson"]
        conn.execute(text("""
            UPDATE districts d
            SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)))
            FROM regions r
            WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
        """), {"gj": json.dumps(gj), "region": REGION, "name": db_name})
        a = conn.execute(text("""
            SELECT ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1)
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.name = :name
        """), {"region": REGION, "name": db_name}).scalar()
        print(f"  OK: {a} km2")
        time.sleep(1.5)

    conn.execute(text("""
        UPDATE districts SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
        WHERE region_id = :rid AND geom IS NOT NULL
    """), {"rid": rid})

print("Done!")
