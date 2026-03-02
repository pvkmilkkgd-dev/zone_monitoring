# -*- coding: utf-8 -*-
"""Перезагрузить Ботлихский и Сергокалинский районы из Overpass."""
import sys
import io
import json
import time
import urllib.request
import urllib.parse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

engine = sa.create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
TARGETS = ["Ботлихский муниципальный район", "Сергокалинский муниципальный район"]

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

def normalize(n):
    n = (n or "").lower().replace("муниципальный район", "").replace("район", "").replace("ё", "е").strip()
    while "  " in n:
        n = n.replace("  ", " ")
    return n

def main():
    q = '[out:json][timeout:60];area["ISO3166-2"="RU-DA"]->.d;(relation["boundary"="administrative"]["admin_level"="6"](area.d););out tags;'
    result = overpass_query(q)
    mapping = {}
    for el in result.get("elements", []):
        name = el.get("tags", {}).get("name") or el.get("tags", {}).get("name:ru") or ""
        for t in TARGETS:
            if normalize(name) == normalize(t) or (normalize(name) in normalize(t)):
                mapping.setdefault(t, []).append(el["id"])
                break
    print("Found:", mapping)
    with engine.begin() as conn:
        for db_name, osm_ids in mapping.items():
            best = None
            best_area = 0
            for oid in osm_ids:
                time.sleep(1.1)
                d = nominatim_lookup(oid)
                if not d or not d.get("geojson"):
                    continue
                gj = d["geojson"]
                if gj.get("type") not in ("Polygon", "MultiPolygon"):
                    continue
                a = conn.execute(text("SELECT ST_Area(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)::geography)/1e6"), {"g": json.dumps(gj)}).scalar()
                if a and a > best_area:
                    best_area = a
                    best = gj
            if best:
                conn.execute(text("""
                    UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                    FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                """), {"g": json.dumps(best), "region": REGION, "name": db_name})
                print(f"OK {db_name}: {best_area:.0f} km2")
    print("Done")

if __name__ == "__main__":
    main()
