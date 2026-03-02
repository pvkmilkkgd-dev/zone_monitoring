# -*- coding: utf-8 -*-
"""Загрузить Чукотский район — последний."""
import sys, io, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

REGION = "Чукотский автономный округ"
engine = create_engine(settings.DATABASE_URL)

OSM_ID = 1949884
DB_NAME = "Чукотский муниципальный район"

print(f"Loading R{OSM_ID} ({DB_NAME})...")
url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{OSM_ID}&format=json&polygon_geojson=1"
req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
try:
    resp = urllib.request.urlopen(req, timeout=180)
    data = json.loads(resp.read().decode())
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

if not data or not data[0].get("geojson"):
    print("No geom!")
    sys.exit(1)

gj = data[0]["geojson"]
print(f"  type={gj['type']}")

with engine.begin() as conn:
    rid = str(conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())
    conn.execute(text("""
        UPDATE districts d
        SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326)))
        FROM regions r
        WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
    """), {"gj": json.dumps(gj), "region": REGION, "name": DB_NAME})

    conn.execute(text("""
        UPDATE districts SET geom_simplified = ST_SimplifyPreserveTopology(geom, 0.01)
        WHERE region_id = :rid AND geom IS NOT NULL
    """), {"rid": rid})

    # Final check
    rows = conn.execute(text("""
        SELECT d.name,
               ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1) AS area,
               ST_NumGeometries(d.geom) AS parts,
               ST_NPoints(d.geom) AS pts
        FROM districts d WHERE d.region_id = :rid ORDER BY d.name
    """), {"rid": rid}).fetchall()
    total = 0.0
    print("\nИтоги:")
    for r in rows:
        area = float(r[1]) if r[1] else 0
        total += area
        flag = f" [{r[2]} частей]" if r[2] > 1 else ""
        print(f"  {r[0]:<45s} {area:>10.1f} km2  {r[3]:>6} pts{flag}")
    print(f"\n  ВСЕГО: {total:.1f} km2")
print("Done!")
