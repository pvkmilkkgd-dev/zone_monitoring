"""
Load OLD (pre-2020) міська рада boundaries for DNR city okrugs.
These boundaries exactly fill the holes in the old raion polygons.
"""
import requests
import json
import time
import sqlalchemy as sa
from sqlalchemy import text

DB_URL = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"
engine = sa.create_engine(DB_URL)

# Mapping: DNR ГО name -> old OSM relation ID (міська рада)
GO_TO_OLD_CITY_RADA = {
    "городской округ Горловка":    2912085,   # Горлівська міська рада
    "городской округ Дебальцево":  2875299,   # Дебальцівська міська рада
    "городской округ Докучаевск":  2899741,   # Докучаєвська міська рада
    "городской округ Донецк":      3936633,   # Донецька міська рада
    "городской округ Енакиево":    2912117,   # Єнакієвська міська рада
    "городской округ Краматорск":  2908424,   # Краматорська міська рада
    "городской округ Макеевка":    2431155,   # Макіївська міська рада
    "городской округ Мариуполь":   2900753,   # Маріупольська міська рада
    "городской округ Снежное":     2913319,   # Сніжнянська міська рада
    "городской округ Торез":       9449033,   # Торезька міська рада
    "городской округ Харцызск":    2906253,   # Харцизька міська рада
}

# Иловайск - not a separate city council in old system, skip for now


def get_geojson_from_nominatim(relation_id):
    """Try to get geometry from Nominatim by OSM relation ID."""
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        "osm_ids": f"R{relation_id}",
        "format": "geojson",
        "polygon_geojson": 1
    }
    headers = {"User-Agent": "ZoneMonitoring/1.0"}
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("features") and len(data["features"]) > 0:
        geom = data["features"][0].get("geometry")
        if geom and geom["type"] in ("Polygon", "MultiPolygon"):
            return geom
    return None


def get_geojson_from_overpass_historical(relation_id):
    """Get historical geometry from Overpass API (pre-2020 data)."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
[out:json][timeout:120][date:"2020-06-01T00:00:00Z"];
relation({relation_id});
(._;>;);
out body;
"""
    resp = requests.post(overpass_url, data={"data": query})
    if resp.status_code != 200:
        print(f"  Overpass error: {resp.status_code}")
        return None

    data = resp.json()
    elements = data.get("elements", [])

    nodes = {}
    ways = {}
    relation = None

    for el in elements:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
        elif el["type"] == "way":
            ways[el["id"]] = el.get("nodes", [])
        elif el["type"] == "relation":
            relation = el

    if not relation:
        print(f"  No relation found in Overpass response")
        return None

    outer_ways = []
    inner_ways = []
    for member in relation.get("members", []):
        if member["type"] == "way":
            role = member.get("role", "")
            way_nodes = ways.get(member["ref"], [])
            coords = [nodes[n] for n in way_nodes if n in nodes]
            if len(coords) < 3:
                continue
            if role == "inner":
                inner_ways.append(coords)
            else:
                outer_ways.append(coords)

    if not outer_ways:
        print(f"  No outer ways found")
        return None

    rings = merge_ways_into_rings(outer_ways)
    inner_rings = merge_ways_into_rings(inner_ways) if inner_ways else []

    if not rings:
        print(f"  Could not form rings from outer ways")
        return None

    if len(rings) == 1 and not inner_rings:
        return {"type": "Polygon", "coordinates": [rings[0]]}
    else:
        if len(rings) == 1:
            coords = [rings[0]] + inner_rings
            return {"type": "Polygon", "coordinates": coords}
        else:
            polygons = []
            for ring in rings:
                polygons.append([ring])
            if inner_rings and polygons:
                polygons[0].extend(inner_rings)
            return {"type": "MultiPolygon", "coordinates": polygons}


def merge_ways_into_rings(ways_coords):
    """Merge way coordinate lists into closed rings."""
    if not ways_coords:
        return []

    rings = []
    remaining = []
    for coords in ways_coords:
        if len(coords) >= 4 and coords[0] == coords[-1]:
            rings.append(coords)
        else:
            remaining.append(list(coords))

    max_iterations = len(remaining) * len(remaining) + 1
    iteration = 0
    while remaining and iteration < max_iterations:
        iteration += 1
        merged = False
        for i in range(len(remaining)):
            for j in range(len(remaining)):
                if i == j:
                    continue
                if remaining[i][-1] == remaining[j][0]:
                    remaining[i].extend(remaining[j][1:])
                    remaining.pop(j)
                    merged = True
                    break
                elif remaining[i][-1] == remaining[j][-1]:
                    remaining[i].extend(reversed(remaining[j][:-1]))
                    remaining.pop(j)
                    merged = True
                    break
                elif remaining[i][0] == remaining[j][-1]:
                    remaining[j].extend(remaining[i][1:])
                    remaining.pop(i)
                    merged = True
                    break
                elif remaining[i][0] == remaining[j][0]:
                    remaining[i] = list(reversed(remaining[i]))
                    remaining[i].extend(remaining[j][1:])
                    remaining.pop(j)
                    merged = True
                    break
            if merged:
                break

        if not merged:
            break

        new_remaining = []
        for coords in remaining:
            if len(coords) >= 4 and coords[0] == coords[-1]:
                rings.append(coords)
            else:
                new_remaining.append(coords)
        remaining = new_remaining

    for coords in remaining:
        if len(coords) >= 4:
            coords.append(coords[0])
            rings.append(coords)

    return rings


def main():
    print("=" * 80)
    print("Loading old miska rada boundaries for DNR city okrugs")
    print("=" * 80)

    with engine.begin() as conn:
        for go_name, relation_id in GO_TO_OLD_CITY_RADA.items():
            # Get current area
            result = conn.execute(text("""
                SELECT ROUND(ST_Area(d.geom::geography)/1000000) as area_km2
                FROM districts d JOIN regions r ON d.region_id = r.id
                WHERE r.name LIKE '%Донецк%' AND d.name = :name AND d.geom IS NOT NULL
            """), {"name": go_name})
            row = result.fetchone()
            current_area = int(row[0]) if row else 0

            print(f"\n{go_name}: current area = {current_area} km2")

            # Try Nominatim first
            print(f"  Trying Nominatim R{relation_id}...")
            geojson = get_geojson_from_nominatim(relation_id)
            time.sleep(1.1)

            if not geojson:
                print(f"  Nominatim failed. Trying Overpass historical...")
                geojson = get_geojson_from_overpass_historical(relation_id)
                time.sleep(2)

            if geojson:
                geojson_str = json.dumps(geojson)
                conn.execute(text("""
                    UPDATE districts d
                    SET geom = ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
                    FROM regions r
                    WHERE d.region_id = r.id
                      AND r.name LIKE '%Донецк%'
                      AND d.name = :name
                """), {"geojson": geojson_str, "name": go_name})

                result = conn.execute(text("""
                    SELECT ROUND(ST_Area(d.geom::geography)/1000000) as area_km2,
                           ST_NPoints(d.geom) as npoints
                    FROM districts d JOIN regions r ON d.region_id = r.id
                    WHERE r.name LIKE '%Донецк%' AND d.name = :name
                """), {"name": go_name})
                row = result.fetchone()
                print(f"  -> Updated: {int(row[0])} km2, {row[1]} points")
            else:
                print(f"  FAILED: Could not load geometry")

    # Final summary
    print("\n" + "=" * 80)
    print("Final state of all DNR districts:")
    print("=" * 80)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT d.name,
                   ROUND(ST_Area(d.geom::geography)/1000000) as area_km2,
                   ST_NPoints(d.geom) as npoints
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name LIKE '%Донецк%'
              AND d.geom IS NOT NULL
            ORDER BY d.name
        """)).fetchall()
        total_area = 0
        print(f"\n{'Name':55s} | {'Area km2':>10s} | {'Points':>8s}")
        print("-" * 80)
        for r in rows:
            area = int(r[1])
            total_area += area
            print(f"{r[0]:55s} | {area:10d} | {r[1]:8.0f}")
        print("-" * 80)
        print(f"{'TOTAL':55s} | {total_area:10d} |")


if __name__ == "__main__":
    main()
