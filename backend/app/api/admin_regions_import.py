import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db

router = APIRouter(prefix="/admin/regions", tags=["admin"])

MAX_BYTES = 25 * 1024 * 1024  # 25 MB


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
        feature = features[0]
    elif doc.get("type") == "Feature":
        feature = doc
    else:
        raise HTTPException(status_code=400, detail="Ожидался GeoJSON FeatureCollection или Feature")

    props = feature.get("properties") or {}
    name = (props.get("name") or "").strip()
    code = (props.get("code") or "").strip() or None
    geom = feature.get("geometry")

    if not name:
        raise HTTPException(status_code=400, detail="properties.name обязателен")
    if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
        raise HTTPException(status_code=400, detail="geometry должен быть Polygon или MultiPolygon")

    geom_json = json.dumps(geom, ensure_ascii=False)

    # Используем правильную структуру таблицы: geom, geom_simplified, bbox, name_original
    if code:
        q = text(
            """
            INSERT INTO regions (id, name, code, name_original, geom, geom_simplified, bbox, created_at, updated_at, is_active)
            VALUES (
                gen_random_uuid(), 
                :name, 
                :code,
                :name_original,
                ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                ST_Multi(
                    ST_CollectionExtract(
                        ST_SimplifyPreserveTopology(
                            ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                            0.05
                        ),
                        3
                    )
                ),
                ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                NOW(),
                NOW(),
                true
            )
            ON CONFLICT (code)
            DO UPDATE SET
                name = EXCLUDED.name,
                name_original = EXCLUDED.name_original,
                geom = EXCLUDED.geom,
                geom_simplified = EXCLUDED.geom_simplified,
                bbox = EXCLUDED.bbox,
                updated_at = NOW()
            RETURNING id::text as id, name, code;
        """
        )
        row = db.execute(
            q, 
            {
                "name": name, 
                "code": code, 
                "name_original": name,
                "geom": geom_json
            }
        ).mappings().first()
    else:
        q = text(
            """
            WITH up AS (
              SELECT id FROM regions WHERE name = :name LIMIT 1
            )
            INSERT INTO regions (id, name, name_original, geom, geom_simplified, bbox, created_at, updated_at, is_active)
            SELECT 
                gen_random_uuid(), 
                :name,
                :name_original,
                ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                ST_Multi(
                    ST_CollectionExtract(
                        ST_SimplifyPreserveTopology(
                            ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                            0.05
                        ),
                        3
                    )
                ),
                ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                NOW(),
                NOW(),
                true
            WHERE NOT EXISTS (SELECT 1 FROM up)
            RETURNING id::text as id, name, code
        """
        )
        row = db.execute(
            q, 
            {
                "name": name, 
                "name_original": name,
                "geom": geom_json
            }
        ).mappings().first()

        if row is None:
            q2 = text(
                """
                UPDATE regions
                SET 
                    geom = ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326),
                    geom_simplified = ST_Multi(
                        ST_CollectionExtract(
                            ST_SimplifyPreserveTopology(
                                ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)),
                                0.05
                            ),
                            3
                        )
                    ),
                    bbox = ST_Envelope(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))),
                    updated_at = NOW()
                WHERE name = :name
                RETURNING id::text as id, name, code;
            """
            )
            row = db.execute(q2, {"name": name, "geom": geom_json}).mappings().first()

    db.commit()
    return {"ok": True, "region": row}
