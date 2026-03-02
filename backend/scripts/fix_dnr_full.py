"""
Load correct OLD (pre-2020) raion boundaries for DNR municipal okrugs.

Uses OSM historical data via Overpass API [date:"2020-06-01T00:00:00Z"].
First checks Nominatim by relation ID, then falls back to Overpass + osm2geojson.
"""
import requests
import json
import time
import sqlalchemy as sa
from sqlalchemy import text

DB_URL = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"
engine = sa.create_engine(DB_URL)

# Mapping: DNR МО name -> old OSM relation ID (pre-2020 raion)
MO_TO_OLD_RAION = {
    "Александровский муниципальный округ":       1742307,  # Олександрівський район
    "Амвросиевский муниципальный округ":          1742298,  # Амвросіївський район
    "Артемовский муниципальный округ":            1742299,  # Бахмутський район
    "Великоновоселковский муниципальный округ":   1742286,  # Великоновосілківський район
    "Волновахский муниципальный округ":           1742287,  # Волноваський район
    "Володарский муниципальный округ":            1742300,  # Нікольський район (ex-Володарський)
    "Добропольский муниципальный округ":          1742301,  # Добропільський район
    "Константиновский муниципальный округ":       1742302,  # Костянтинівський район
    "Красноармейский муниципальный округ":        1742303,  # Покровський район (ex-Красноармійський)
    "Краснолиманский муниципальный округ":        1742304,  # Лиманський район (ex-Краснолиманський)
    "Кураховский муниципальный округ":            1742305,  # Мар'їнський район
    "Мангушский муниципальный округ":             1742308,  # Мангушський район
    "Новоазовский муниципальный округ":           1742306,  # Новоазовський район
    "Славянский муниципальный округ":             1742309,  # Слов'янський район
    "Старобешевский муниципальный округ":         1742310,  # Старобешівський район
    "Тельмановский муниципальный округ":          1742311,  # Тельманівський район
    "Шахтерский муниципальный округ":             1742312,  # Шахтарський район
    "Ясиноватский муниципальный округ":           1742313,  # Ясинуватський район
}

# Also update city okrugs with their proper міська рада boundaries
GO_TO_OLD_CITY = {
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


def get_geojson_from_nominatim(relation_id):
    """Try to get geometry from Nominatim by OSM relation ID."""
    url = f"https://nominatim.openstreetmap.org/lookup"
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

    # Build node index
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

    # Collect outer and inner ways
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

    # Merge ways into rings
    rings = merge_ways_into_rings(outer_ways)
    inner_rings = merge_ways_into_rings(inner_ways) if inner_ways else []

    if not rings:
        print(f"  Could not form rings from outer ways")
        return None

    if len(rings) == 1 and not inner_rings:
        return {"type": "Polygon", "coordinates": [rings[0]]}
    else:
        # MultiPolygon or Polygon with holes
        if len(rings) == 1:
            coords = [rings[0]] + inner_rings
            return {"type": "Polygon", "coordinates": coords}
        else:
            polygons = []
            for ring in rings:
                polygons.append([ring])
            # Simple approach: add inner rings to the first polygon
            if inner_rings and polygons:
                polygons[0].extend(inner_rings)
            return {"type": "MultiPolygon", "coordinates": polygons}


def merge_ways_into_rings(ways_coords):
    """Merge way coordinate lists into closed rings."""
    if not ways_coords:
        return []

    # Check if any single way is already a ring
    rings = []
    remaining = []
    for coords in ways_coords:
        if len(coords) >= 4 and coords[0] == coords[-1]:
            rings.append(coords)
        else:
            remaining.append(list(coords))

    # Try to merge remaining ways into rings
    max_iterations = len(remaining) * len(remaining) + 1
    iteration = 0
    while remaining and iteration < max_iterations:
        iteration += 1
        merged = False
        for i in range(len(remaining)):
            for j in range(len(remaining)):
                if i == j:
                    continue
                # Try to connect way i to way j
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

        # Check for completed rings
        new_remaining = []
        for coords in remaining:
            if len(coords) >= 4 and coords[0] == coords[-1]:
                rings.append(coords)
            else:
                new_remaining.append(coords)
        remaining = new_remaining

    # Any unclosed remaining ways - try to close them if they're long enough
    for coords in remaining:
        if len(coords) >= 4:
            # Force close
            coords.append(coords[0])
            rings.append(coords)

    return rings


def update_district_geom(conn, district_name, geojson_geom):
    """Update district geometry in database."""
    geojson_str = json.dumps(geojson_geom)
    result = conn.execute(text("""
        UPDATE districts d
        SET geom = ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
        FROM regions r
        WHERE d.region_id = r.id
          AND r.name LIKE '%Донецк%'
          AND d.name = :name
        RETURNING d.id
    """), {"geojson": geojson_str, "name": district_name})
    return result.fetchone()


def check_area(conn, district_name):
    """Get area of district in km2."""
    result = conn.execute(text("""
        SELECT ROUND(ST_Area(d.geom::geography)/1000000) as area_km2,
               ST_NPoints(d.geom) as npoints
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.name = :name
          AND d.geom IS NOT NULL
    """), {"name": district_name})
    row = result.fetchone()
    return (int(row[0]), row[1]) if row else (0, 0)


def main():
    print("=" * 80)
    print("Loading correct raion boundaries for DNR municipal okrugs")
    print("=" * 80)

    with engine.begin() as conn:
        # Process municipal okrugs (these need old raion boundaries)
        print("\n--- Municipal okrugs (old raion boundaries) ---\n")
        for mo_name, relation_id in MO_TO_OLD_RAION.items():
            current_area, _ = check_area(conn, mo_name)
            print(f"{mo_name}: current area = {current_area} km2")

            # First try Nominatim (works if relation still exists)
            print(f"  Trying Nominatim R{relation_id}...")
            geojson = get_geojson_from_nominatim(relation_id)
            time.sleep(1.1)  # Nominatim rate limit

            if not geojson:
                print(f"  Nominatim failed. Trying Overpass historical...")
                geojson = get_geojson_from_overpass_historical(relation_id)
                time.sleep(2)  # Be nice to Overpass

            if geojson:
                update_district_geom(conn, mo_name, geojson)
                new_area, npoints = check_area(conn, mo_name)
                print(f"  -> Updated: {new_area} km2, {npoints} points")
                if new_area < 50:
                    print(f"  WARNING: Area seems too small!")
            else:
                print(f"  FAILED: Could not load geometry")

        # Process city okrugs
        print("\n--- City okrugs (міська рада boundaries) ---\n")
        for go_name, relation_id in GO_TO_OLD_CITY.items():
            current_area, _ = check_area(conn, go_name)
            print(f"{go_name}: current area = {current_area} km2")

            # Only update if area seems wrong (too small)
            if current_area >= 10:
                print(f"  Skipping (area OK)")
                continue

            print(f"  Trying Nominatim R{relation_id}...")
            geojson = get_geojson_from_nominatim(relation_id)
            time.sleep(1.1)

            if not geojson:
                print(f"  Nominatim failed. Trying Overpass historical...")
                geojson = get_geojson_from_overpass_historical(relation_id)
                time.sleep(2)

            if geojson:
                update_district_geom(conn, go_name, geojson)
                new_area, npoints = check_area(conn, go_name)
                print(f"  -> Updated: {new_area} km2, {npoints} points")
            else:
                print(f"  FAILED: Could not load geometry")

    print("\n" + "=" * 80)
    print("Done! Running final check...")
    print("=" * 80)

    # Final summary
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
            flag = " !" if area < 50 else ""
            print(f"{r[0]:55s} | {area:10d} | {r[2]:8d}{flag}")
        print("-" * 80)
        print(f"{'TOTAL':55s} | {total_area:10d} |")
        print(f"\nExpected total area of Donetsk Oblast: ~26,500 km2")


if __name__ == "__main__":
    main()
