import json
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db

router = APIRouter(prefix="/admin/regions", tags=["admin"])

MAX_BYTES = 50 * 1024 * 1024  # 50 MB


def _region_name_from_feature(props: dict) -> str:
    return (
        props.get("name")
        or props.get("NAME_1")
        or props.get("NL_NAME_1")
        or props.get("display_name")
        or ""
    ).strip()


def _district_name(props: dict) -> str:
    return (
        props.get("name")
        or props.get("NAME_2")
        or props.get("NL_NAME_2")
        or props.get("NAME_3")
        or props.get("NL_NAME_3")
        or ""
    ).strip()


def _parse_population(val) -> int:
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


def _upsert_region(db: Session, name: str, code: str | None, geom_json: str) -> dict:
    """Insert or update region, return {id, name, code}."""
    if code:
        q = text("""
            INSERT INTO regions (id, name, code, name_original, geom, geom_simplified, bbox, created_at, updated_at, is_active)
            VALUES (
                gen_random_uuid(), :name, :code, :name_original,
                ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                ST_Multi(ST_CollectionExtract(
                    ST_SimplifyPreserveTopology(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 0.05), 3)),
                ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                NOW(), NOW(), true
            )
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name, name_original = EXCLUDED.name_original,
                geom = EXCLUDED.geom, geom_simplified = EXCLUDED.geom_simplified,
                bbox = EXCLUDED.bbox, updated_at = NOW()
            RETURNING id::text as id, name, code;
        """)
        return dict(db.execute(q, {"name": name, "code": code, "name_original": name, "geom": geom_json}).mappings().first())
    else:
        q = text("""
            WITH existing AS (SELECT id FROM regions WHERE name = :name LIMIT 1)
            INSERT INTO regions (id, name, name_original, geom, geom_simplified, bbox, created_at, updated_at, is_active)
            SELECT gen_random_uuid(), :name, :name_original,
                ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                ST_Multi(ST_CollectionExtract(
                    ST_SimplifyPreserveTopology(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 0.05), 3)),
                ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                NOW(), NOW(), true
            WHERE NOT EXISTS (SELECT 1 FROM existing)
            RETURNING id::text as id, name, code
        """)
        row = db.execute(q, {"name": name, "name_original": name, "geom": geom_json}).mappings().first()
        if row:
            return dict(row)
        q2 = text("""
            UPDATE regions SET
                geom = ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                geom_simplified = ST_Multi(ST_CollectionExtract(
                    ST_SimplifyPreserveTopology(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 0.05), 3)),
                bbox = ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                updated_at = NOW()
            WHERE name = :name
            RETURNING id::text as id, name, code;
        """)
        return dict(db.execute(q2, {"name": name, "geom": geom_json}).mappings().first())


def _insert_districts(db: Session, region_id: str, features: list[dict]) -> int:
    """Clear old districts and insert new ones from polygon features."""
    db.execute(text("DELETE FROM cities WHERE region_id = :rid"), {"rid": region_id})
    db.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})

    inserted = 0
    for feat in features:
        name = _district_name(feat.get("properties") or {})
        if not name:
            continue
        geom = feat.get("geometry")
        if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        geom_json = json.dumps(geom, ensure_ascii=False)
        db.execute(text("""
            INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
            VALUES (:id, :rid, :name,
                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                    ST_SimplifyPreserveTopology(
                        ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                    NOW())
        """), {"id": str(uuid4()), "rid": region_id, "name": name, "geojson": geom_json})
        inserted += 1
    return inserted


def _insert_cities(db: Session, region_id: str, features: list[dict]) -> int:
    """Insert city Point features."""
    inserted = 0
    cities = []
    for feat in features:
        props = feat.get("properties") or {}
        name = (props.get("name") or "").strip()
        if not name:
            continue
        geom = feat.get("geometry")
        if not geom or geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        pop = _parse_population(props.get("population", 0))
        cities.append({"name": name, "population": pop, "lat": lat, "lon": lon})

    cities.sort(key=lambda c: c["population"], reverse=True)
    for i, city in enumerate(cities):
        db.execute(text("""
            INSERT INTO cities (region_id, name, population, lat, lon, importance)
            VALUES (:rid, :name, :pop, :lat, :lon, :imp)
        """), {
            "rid": region_id,
            "name": city["name"],
            "pop": city["population"],
            "lat": city["lat"],
            "lon": city["lon"],
            "imp": i + 1,
        })
        inserted += 1
    return inserted


@router.post("/import")
async def import_region_geojson(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(get_current_admin_user),
):
    if not file.filename.lower().endswith((".geojson", ".json")):
        raise HTTPException(status_code=400, detail="Нужен файл .geojson или .json")

    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Файл слишком большой")

    try:
        doc = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Не смог прочитать JSON")

    if doc.get("type") == "FeatureCollection":
        features = doc.get("features") or []
        if not features:
            raise HTTPException(status_code=400, detail="FeatureCollection пустой")
    elif doc.get("type") == "Feature":
        features = [doc]
    else:
        raise HTTPException(status_code=400, detail="Ожидался GeoJSON FeatureCollection или Feature")

    polygons = [f for f in features if f.get("geometry", {}).get("type") in ("Polygon", "MultiPolygon")]
    points = [f for f in features if f.get("geometry", {}).get("type") == "Point"]

    if not polygons:
        raise HTTPException(status_code=400, detail="Нет полигонов в файле")

    # --- Determine region name ---
    first_props = (polygons[0].get("properties") or {})
    if len(polygons) == 1:
        region_name = _region_name_from_feature(first_props)
    else:
        region_name = (
            first_props.get("NAME_1")
            or first_props.get("NL_NAME_1")
            or first_props.get("region")
            or first_props.get("region_name")
            or ""
        ).strip()
        if not region_name:
            region_name = _region_name_from_feature(first_props)

    if not region_name:
        raise HTTPException(status_code=400, detail="Не удалось определить название региона из properties (name / NAME_1 / NL_NAME_1)")

    code = (first_props.get("code") or first_props.get("ISO_1") or first_props.get("HASC_1") or "").strip() or None

    # --- Single polygon → region only ---
    if len(polygons) == 1:
        geom_json = json.dumps(polygons[0]["geometry"], ensure_ascii=False)
        region_row = _upsert_region(db, region_name, code, geom_json)
        cities_count = 0
        if points:
            cities_count = _insert_cities(db, region_row["id"], points)
        db.commit()
        return {
            "ok": True,
            "region": region_row,
            "districts_loaded": 0,
            "cities_loaded": cities_count,
        }

    # --- Multiple polygons → region (union) + districts ---
    region_geom_json = json.dumps(polygons[0]["geometry"], ensure_ascii=False)
    region_row = _upsert_region(db, region_name, code, region_geom_json)
    region_id = region_row["id"]

    districts_count = _insert_districts(db, region_id, polygons)

    # Region geometry = union of all districts
    db.execute(text("""
        UPDATE regions SET
            geom = sub.ugeom,
            geom_simplified = ST_Multi(ST_CollectionExtract(
                ST_SimplifyPreserveTopology(ST_MakeValid(sub.ugeom), 0.05), 3)),
            bbox = ST_Envelope(ST_MakeValid(sub.ugeom)),
            updated_at = NOW()
        FROM (
            SELECT ST_Multi(ST_MakeValid(ST_Union(geom))) AS ugeom
            FROM districts WHERE region_id = :rid AND geom IS NOT NULL
        ) sub
        WHERE regions.id = CAST(:rid AS uuid)
    """), {"rid": region_id})

    cities_count = 0
    if points:
        cities_count = _insert_cities(db, region_id, points)

    db.commit()
    return {
        "ok": True,
        "region": region_row,
        "districts_loaded": districts_count,
        "cities_loaded": cities_count,
    }
