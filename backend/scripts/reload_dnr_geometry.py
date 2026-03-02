"""
Полная перезагрузка геометрии районов ДНР из OSM.

1. Загружает границы 18 муниципальных округов (старые районы Донецкой области)
2. Загружает границы 12 городских округов (міські ради)
3. Удаляет внутренние кольца (дырки) у МО и ГО
4. Делает геометрии валидными
5. Удаляет мелкие фрагменты у multi-part полигонов
"""
import requests
import json
import time
import sqlalchemy as sa
from sqlalchemy import text

DB_URL = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"
engine = sa.create_engine(DB_URL)

MO_TO_OLD_RAION = {
    "Александровский муниципальный округ":       1742307,
    "Амвросиевский муниципальный округ":          1742298,
    "Артемовский муниципальный округ":            1742299,
    "Великоновоселковский муниципальный округ":   1742286,
    "Волновахский муниципальный округ":           1742287,
    "Володарский муниципальный округ":            1742300,
    "Добропольский муниципальный округ":          1742301,
    "Константиновский муниципальный округ":       1742302,
    "Красноармейский муниципальный округ":        1742303,
    "Краснолиманский муниципальный округ":        1742304,
    "Кураховский муниципальный округ":            1742305,
    "Мангушский муниципальный округ":             1742308,
    "Новоазовский муниципальный округ":           1742306,
    "Славянский муниципальный округ":             1742309,
    "Старобешевский муниципальный округ":         1742310,
    "Тельмановский муниципальный округ":          1742311,
    "Шахтерский муниципальный округ":             1742312,
    "Ясиноватский муниципальный округ":           1742313,
}

GO_TO_OLD_CITY_RADA = {
    "городской округ Горловка":    2912085,
    "городской округ Дебальцево":  2875299,
    "городской округ Докучаевск":  2899741,
    "городской округ Донецк":      3936633,
    "городской округ Енакиево":    2912117,
    "городской округ Краматорск":  2908424,
    "городской округ Макеевка":    2431155,
    "городской округ Мариуполь":   2900753,
    "городской округ Снежное":     2913319,
    "городской округ Торез":       9449033,
    "городской округ Харцызск":    2906253,
}


def get_geojson_from_nominatim(relation_id):
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {"osm_ids": f"R{relation_id}", "format": "geojson", "polygon_geojson": 1}
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
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
[out:json][timeout:120][date:"2020-06-01T00:00:00Z"];
relation({relation_id});
(._;>;);
out body;
"""
    resp = requests.post(overpass_url, data={"data": query})
    if resp.status_code != 200:
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
        return None
    outer_ways = []
    inner_ways = []
    for member in relation.get("members", []):
        if member["type"] == "way":
            way_nodes = ways.get(member["ref"], [])
            coords = [nodes[n] for n in way_nodes if n in nodes]
            if len(coords) < 3:
                continue
            if member.get("role") == "inner":
                inner_ways.append(coords)
            else:
                outer_ways.append(coords)
    if not outer_ways:
        return None
    rings = merge_ways_into_rings(outer_ways)
    inner_rings = merge_ways_into_rings(inner_ways) if inner_ways else []
    if not rings:
        return None
    if len(rings) == 1 and not inner_rings:
        return {"type": "Polygon", "coordinates": [rings[0]]}
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": [rings[0]] + inner_rings}
    polygons = [[r] for r in rings]
    if inner_rings and polygons:
        polygons[0].extend(inner_rings)
    return {"type": "MultiPolygon", "coordinates": polygons}


def merge_ways_into_rings(ways_coords):
    if not ways_coords:
        return []
    rings = []
    remaining = []
    for coords in ways_coords:
        if len(coords) >= 4 and coords[0] == coords[-1]:
            rings.append(coords)
        else:
            remaining.append(list(coords))
    max_iter = len(remaining) ** 2 + 1
    for _ in range(max_iter):
        if not remaining:
            break
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
                    remaining[i] = list(reversed(remaining[i])) + remaining[j][1:]
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


def update_district_geom(conn, name, geojson_geom):
    geojson_str = json.dumps(geojson_geom)
    conn.execute(text("""
        UPDATE districts d
        SET geom = ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
        FROM regions r
        WHERE d.region_id = r.id AND r.name LIKE '%Донецк%' AND d.name = :name
    """), {"geojson": geojson_str, "name": name})


def main():
    print("=" * 70)
    print("Перезагрузка геометрии районов ДНР из OSM")
    print("=" * 70)

    # --- 1. Муниципальные округи ---
    print("\n[1/5] Загрузка 18 муниципальных округов (старые районы)...")
    with engine.begin() as conn:
        for mo_name, rel_id in MO_TO_OLD_RAION.items():
            geojson = get_geojson_from_nominatim(rel_id)
            time.sleep(1.1)
            if not geojson:
                geojson = get_geojson_from_overpass_historical(rel_id)
                time.sleep(2)
            if geojson:
                update_district_geom(conn, mo_name, geojson)
                r = conn.execute(text("""
                    SELECT ROUND(ST_Area(d.geom::geography)/1000000)
                    FROM districts d JOIN regions r ON d.region_id = r.id
                    WHERE r.name LIKE '%Донецк%' AND d.name = :name
                """), {"name": mo_name}).fetchone()
                print(f"  OK {mo_name}: {int(r[0])} km2")
            else:
                print(f"  FAIL {mo_name} (R{rel_id})")

    # --- 2. Городские округа ---
    print("\n[2/5] Загрузка 12 городских округов (міські ради)...")
    with engine.begin() as conn:
        for go_name, rel_id in GO_TO_OLD_CITY_RADA.items():
            geojson = get_geojson_from_nominatim(rel_id)
            time.sleep(1.1)
            if not geojson:
                geojson = get_geojson_from_overpass_historical(rel_id)
                time.sleep(2)
            if geojson:
                update_district_geom(conn, go_name, geojson)
                r = conn.execute(text("""
                    SELECT ROUND(ST_Area(d.geom::geography)/1000000)
                    FROM districts d JOIN regions r ON d.region_id = r.id
                    WHERE r.name LIKE '%Донецк%' AND d.name = :name
                """), {"name": go_name}).fetchone()
                print(f"  OK {go_name}: {int(r[0])} km2")
            else:
                print(f"  FAIL {go_name} (R{rel_id})")

    # --- 3. Удаление внутренних колец (дырки) ---
    print("\n[3/5] Удаление внутренних колец у МО и ГО...")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE districts d
            SET geom = (SELECT ST_SetSRID(ST_Collect(ST_MakePolygon(ST_ExteriorRing((dump).geom))), 4326)
                       FROM ST_Dump(d.geom) AS dump)
            FROM regions r
            WHERE d.region_id = r.id AND r.name LIKE '%Донецк%' AND d.geom IS NOT NULL
        """))
    print("  Готово.")

    # --- 4. Валидность геометрий ---
    print("\n[4/5] Приведение геометрий к валидному виду...")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE districts d
            SET geom = ST_Multi(ST_Buffer(ST_MakeValid(d.geom), 0))
            FROM regions r
            WHERE d.region_id = r.id AND r.name LIKE '%Донецк%' AND d.geom IS NOT NULL
        """))
    print("  Готово.")

    # --- 5. Удаление мелких фрагментов ---
    print("\n[5/5] Удаление мелких фрагментов у multi-part полигонов...")
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT d.id, d.name, ST_NumGeometries(d.geom), ST_AsGeoJSON(d.geom)::text
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name LIKE '%Донецк%' AND d.geom IS NOT NULL AND ST_NumGeometries(d.geom) > 1
        """)).fetchall()
        for row in rows:
            did, name, num_parts = row[0], row[1], row[2]
            geojson = json.loads(row[3])
            if geojson.get("type") != "MultiPolygon":
                continue
            polys_with_area = []
            for coords in geojson["coordinates"]:
                ring = coords[0]
                n = len(ring)
                area = abs(sum(ring[j][0]*ring[(j+1)%n][1] - ring[(j+1)%n][0]*ring[j][1] for j in range(n))) / 2
                polys_with_area.append((area, coords))
            max_area = max(a for a, _ in polys_with_area)
            significant = [c for a, c in polys_with_area if a >= max_area * 0.01]
            if len(significant) < num_parts:
                new_geojson = {"type": "MultiPolygon", "coordinates": significant} if len(significant) > 1 else {"type": "Polygon", "coordinates": significant[0]}
                conn.execute(text("UPDATE districts SET geom = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)) WHERE id = :id"),
                            {"g": json.dumps(new_geojson), "id": did})
                print(f"  {name}: {num_parts} -> {len(significant)} частей")
    print("  Готово.")

    # Итог
    print("\n" + "=" * 70)
    print("Итог по районам ДНР:")
    print("=" * 70)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT d.name, ROUND(ST_Area(d.geom::geography)/1000000) as area
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name LIKE '%Донецк%' AND d.geom IS NOT NULL
            ORDER BY d.name
        """)).fetchall()
        total = 0
        for r in rows:
            area = int(r[1])
            total += area
            print(f"  {r[0]:55s} | {area:6d} km2")
        print(f"  {'TOTAL':55s} | {total:6d} km2")


if __name__ == "__main__":
    main()
