# -*- coding: utf-8 -*-
"""
Найти дыру между Бабаюртовским и Хасавюртовским районами,
разделить пополам и отдать каждому по половине.
Используем буферный подход: малый буфер обоих, пересечение буферов минус оригиналы = щель.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
D1 = "Бабаюртовский муниципальный район"
D2 = "Хасавюртовский муниципальный район"

def main():
    # Сначала перезагрузим оба района из Overpass (откат предыдущего)
    import json, time, urllib.request, urllib.parse

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

    print("1) Reload from Overpass...")
    q = '[out:json][timeout:60];area["ISO3166-2"="RU-DA"]->.d;(relation["boundary"="administrative"]["admin_level"="6"](area.d););out tags;'
    result = overpass_query(q)

    targets = {D1: None, D2: None}
    for el in result.get("elements", []):
        n = (el.get("tags", {}).get("name") or "")
        for tgt in targets:
            norm_tgt = tgt.lower().replace("муниципальный район", "").strip()
            norm_n = n.lower().replace("муниципальный район", "").strip()
            if norm_tgt == norm_n or norm_n in norm_tgt or norm_tgt in norm_n:
                if not targets[tgt] or el["id"] < targets[tgt]:
                    targets[tgt] = el["id"]

    with engine.begin() as conn:
        for db_name, osm_id in targets.items():
            if not osm_id:
                print(f"  {db_name}: not found in Overpass")
                continue
            time.sleep(1.1)
            d = nominatim_lookup(osm_id)
            if not d or not d.get("geojson"):
                continue
            gj = d["geojson"]
            if gj.get("type") not in ("Polygon", "MultiPolygon"):
                continue
            conn.execute(text("""
                UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
            """), {"g": json.dumps(gj), "region": REGION, "name": db_name})
            a = conn.execute(text("""
                SELECT ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
                FROM districts d JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """), {"region": REGION, "name": db_name}).scalar()
            print(f"  {db_name}: R{osm_id}, {a} km2")

    print("\n2) Find gap...")
    with engine.begin() as conn:
        rid = str(conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())

        # Буфер 2 км от каждого района, пересечение буферов, вычитание всех районов Дагестана
        gap_info = conn.execute(text("""
            WITH d1 AS (
                SELECT d.geom FROM districts d JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :n1
            ),
            d2 AS (
                SELECT d.geom FROM districts d JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :n2
            ),
            buf1 AS (SELECT ST_Buffer(geom::geography, 2000)::geometry AS geom FROM d1),
            buf2 AS (SELECT ST_Buffer(geom::geography, 2000)::geometry AS geom FROM d2),
            buf_overlap AS (
                SELECT ST_Intersection(buf1.geom, buf2.geom) AS geom FROM buf1, buf2
            ),
            all_districts AS (
                SELECT ST_Union(d.geom) AS geom
                FROM districts d WHERE d.region_id = :rid AND d.geom IS NOT NULL
            ),
            gap AS (
                SELECT ST_CollectionExtract(
                    ST_Difference(bo.geom, ad.geom), 3
                ) AS geom
                FROM buf_overlap bo, all_districts ad
            )
            SELECT gap.geom, ROUND((ST_Area(gap.geom::geography)/1000000)::numeric, 2)
            FROM gap WHERE NOT ST_IsEmpty(gap.geom)
        """), {"region": REGION, "n1": D1, "n2": D2, "rid": rid}).fetchone()

        if not gap_info or not gap_info[0]:
            print("  Gap not found")
            return

        gap_geom = gap_info[0]
        gap_area = gap_info[1]
        print(f"  Gap: {gap_area} km2")

        print("\n3) Split gap using Voronoi...")
        # Voronoi: точка ближе к D1 -> D1, точка ближе к D2 -> D2
        for name in [D1, D2]:
            conn.execute(text("""
                WITH target AS (
                    SELECT d.id, ST_Centroid(d.geom) as centroid
                    FROM districts d JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :name
                ),
                other AS (
                    SELECT ST_Centroid(d.geom) as centroid
                    FROM districts d JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :other
                ),
                voronoi AS (
                    SELECT (ST_Dump(
                        ST_VoronoiPolygons(
                            ST_Collect(target.centroid, other.centroid),
                            0,
                            ST_Expand(ST_Envelope(:gap_geom), 1)
                        )
                    )).geom AS cell
                    FROM target, other
                ),
                my_half AS (
                    SELECT ST_CollectionExtract(
                        ST_Intersection(:gap_geom, v.cell), 3
                    ) AS geom
                    FROM voronoi v, target
                    WHERE ST_Contains(v.cell, target.centroid)
                )
                UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, h.geom)))
                FROM target t, my_half h
                WHERE d.id = t.id AND NOT ST_IsEmpty(h.geom)
            """), {"region": REGION, "name": name, "other": D2 if name == D1 else D1, "gap_geom": gap_geom})

        # Заполнить дыры и обновить simplified
        for name in [D1, D2]:
            conn.execute(text("""
                UPDATE districts d SET geom = sub.geom
                FROM (
                    SELECT d.id,
                           ST_Multi(ST_Union(ST_MakePolygon(ST_ExteriorRing((dump).geom)))) AS geom
                    FROM districts d JOIN regions r ON d.region_id = r.id,
                    LATERAL ST_Dump(d.geom) AS dump
                    WHERE r.name = :region AND d.name = :name
                    GROUP BY d.id
                ) sub WHERE d.id = sub.id
            """), {"region": REGION, "name": name})
            conn.execute(text("""
                UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
                FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
            """), {"region": REGION, "name": name})

    print("\n4) Result:")
    with engine.connect() as conn:
        for name in [D1, D2]:
            r = conn.execute(text("""
                SELECT ST_NumGeometries(d.geom), ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
                FROM districts d JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """), {"region": REGION, "name": name}).fetchone()
            print(f"  {name}: {r[0]} parts, {r[1]} km2")

    print("\nOK")

if __name__ == "__main__":
    main()
