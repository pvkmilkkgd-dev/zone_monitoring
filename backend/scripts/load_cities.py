"""
Load one city/town per district from Overpass API.
Downloads all Russian cities/towns with population, then matches each to its district via PostGIS.
Keeps the largest city per district.
"""
import sys
import json
import time
import urllib.request
import urllib.parse

sys.path.insert(0, ".")
from sqlalchemy import create_engine, text
from app.core.config import settings

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = """
[out:json][timeout:180];
area["ISO3166-1"="RU"]->.searchArea;
(
  node["place"="city"]["population"](area.searchArea);
  node["place"="town"]["population"](area.searchArea);
);
out body;
"""


def fetch_overpass():
    print("Fetching cities from Overpass API...")
    data = urllib.parse.urlencode({"data": OVERPASS_QUERY}).encode("utf-8")
    req = urllib.request.Request(OVERPASS_URL, data=data)
    req.add_header("User-Agent", "ZoneMonitoring/1.0")

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=200) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(10 * (attempt + 1))
    raise RuntimeError("Failed to fetch from Overpass after 3 attempts")


def parse_population(val):
    if not val:
        return 0
    s = str(val).replace(" ", "").replace(",", "").replace("\u00a0", "")
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return 0


def main():
    engine = create_engine(settings.DATABASE_URL)

    result = fetch_overpass()
    elements = result.get("elements", [])
    print(f"Got {len(elements)} cities/towns from Overpass")

    cities = []
    for el in elements:
        if el.get("type") != "node":
            continue
        tags = el.get("tags", {})
        name = tags.get("name", "")
        if not name:
            continue
        pop = parse_population(tags.get("population"))
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is None or lon is None:
            continue
        cities.append({
            "name": name,
            "population": pop,
            "lat": lat,
            "lon": lon,
        })

    print(f"Parsed {len(cities)} cities with names")

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM cities"))
        conn.commit()

        # Get all districts with their region_id
        districts = conn.execute(text("""
            SELECT d.id, d.region_id, d.name, d.geom
            FROM districts d
            WHERE d.geom IS NOT NULL
        """)).fetchall()
        print(f"Found {len(districts)} districts")

        # For each city, find which district it belongs to
        # Build a mapping: district_id -> best city (largest population)
        district_best: dict = {}  # district_id -> city dict

        for i, city in enumerate(cities):
            if (i + 1) % 500 == 0:
                print(f"  Matching city {i+1}/{len(cities)}...")

            row = conn.execute(text("""
                SELECT d.id, d.region_id
                FROM districts d
                WHERE d.geom IS NOT NULL
                  AND ST_Contains(d.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                LIMIT 1
            """), {"lon": city["lon"], "lat": city["lat"]}).first()

            if not row:
                continue

            district_id = str(row[0])
            region_id = str(row[1])

            if district_id not in district_best or city["population"] > district_best[district_id]["population"]:
                district_best[district_id] = {
                    "district_id": district_id,
                    "region_id": region_id,
                    "name": city["name"],
                    "population": city["population"],
                    "lat": city["lat"],
                    "lon": city["lon"],
                }

        print(f"Matched cities to {len(district_best)} districts")

        # Insert: one city per district
        for city_data in district_best.values():
            conn.execute(text("""
                INSERT INTO cities (region_id, name, population, lat, lon, importance)
                VALUES (:region_id, :name, :pop, :lat, :lon, 1)
            """), {
                "region_id": city_data["region_id"],
                "name": city_data["name"],
                "pop": city_data["population"],
                "lat": city_data["lat"],
                "lon": city_data["lon"],
            })

        conn.commit()

        # Now rank cities within each region by population for importance
        regions = conn.execute(text("SELECT DISTINCT region_id FROM cities")).fetchall()
        for (region_id,) in regions:
            rows = conn.execute(text("""
                SELECT id, population FROM cities
                WHERE region_id = :rid
                ORDER BY population DESC
            """), {"rid": region_id}).fetchall()

            for i, (cid, _pop) in enumerate(rows):
                importance = i + 1
                conn.execute(text("""
                    UPDATE cities SET importance = :imp WHERE id = :cid
                """), {"imp": importance, "cid": cid})

        conn.commit()

        # Summary
        total = conn.execute(text("SELECT COUNT(*) FROM cities")).scalar()
        print(f"\nTotal: {total} cities (one per district)")

        summary = conn.execute(text("""
            SELECT r.name, COUNT(c.id),
                   string_agg(c.name || ' (' || c.population || ')', ', ' ORDER BY c.importance)
            FROM regions r
            LEFT JOIN cities c ON c.region_id = r.id
            GROUP BY r.name
            HAVING COUNT(c.id) > 0
            ORDER BY r.name
        """)).fetchall()

        for rname, cnt, cities_str in summary:
            print(f"  {rname}: {cnt} cities - {cities_str}")


if __name__ == "__main__":
    main()
