from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db  # ВАЖНО: app., не backend.app.

router = APIRouter(prefix="/maps/ru", tags=["maps"])

# Минимальная обработка: валидация + правильный порядок координат.
# Для геометрий с отрицательными долготами (антимеридиан — Чукотка)
# сдвигаем в диапазон 0..360 через ST_ShiftLongitude.
_geom_expr = """ST_Multi(ST_ForceRHR(ST_MakeValid(
    CASE WHEN ST_XMin(geom) < 0
         THEN ST_ShiftLongitude(geom)
         ELSE geom
    END
)))"""


@router.get("/regions.geojson")
def regions_geojson(db: Session = Depends(get_db)):
    q = text("""
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'properties', jsonb_build_object(
            'id', id,
            'name', name
          ),
          'geometry', ST_AsGeoJSON(
            CASE WHEN ST_XMin(COALESCE(geom_simplified, geom)) < 0
                 THEN ST_ShiftLongitude(COALESCE(geom_simplified, geom))
                 ELSE COALESCE(geom_simplified, geom)
            END
          )::jsonb
        )
      ), '[]'::jsonb)
    ) AS fc
    FROM regions;
    """)
    return db.execute(q).scalar_one()


@router.get("/region/{region_id}/districts.geojson")
def region_districts_geojson(region_id: str, db: Session = Depends(get_db)):
    """
    Возвращает GeoJSON с районами (или городами) для указанного региона.
    Если в БД есть таблица districts или подобная структура, 
    отдаем из неё. Иначе возвращаем сам регион.
    """
    # Проверяем, есть ли данные в таблице districts для этого региона
    check_districts = text("""
        SELECT COUNT(*) FROM districts WHERE region_id = :region_id;
    """)
    districts_count = db.execute(check_districts, {"region_id": region_id}).scalar()
    
    if districts_count > 0:
        q = text(f"""
        SELECT jsonb_build_object(
          'type','FeatureCollection',
          'features', COALESCE(jsonb_agg(
            jsonb_build_object(
              'type','Feature',
              'properties', jsonb_build_object(
                'id', id::text,
                'name', name
              ),
              'geometry', ST_AsGeoJSON({_geom_expr})::jsonb
            )
          ), '[]'::jsonb)
        ) AS fc
        FROM districts
        WHERE region_id = :region_id AND geom IS NOT NULL AND ST_NPoints(geom) > 0;
        """)
        data = db.execute(q, {"region_id": region_id}).scalar_one()
        return JSONResponse(
            content=data,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )
    else:
        # Если нет районов, возвращаем сам регион
        q = text("""
        SELECT jsonb_build_object(
          'type','FeatureCollection',
          'features', jsonb_build_array(
            jsonb_build_object(
              'type','Feature',
              'properties', jsonb_build_object(
                'id', id::text,
                'name', name
              ),
              'geometry', ST_AsGeoJSON(COALESCE(geom_simplified, geom))::jsonb
            )
          )
        ) AS fc
        FROM regions
        WHERE id = :region_id;
        """)
        return db.execute(q, {"region_id": region_id}).scalar_one()


@router.get("/region/{region_id}/cities.json")
def region_cities(region_id: str, db: Session = Depends(get_db)):
    q = text("""
    SELECT json_agg(json_build_object(
        'name', name,
        'population', population,
        'lat', lat,
        'lon', CASE WHEN lon < 0 THEN lon + 360 ELSE lon END,
        'importance', importance
    ) ORDER BY importance)
    FROM cities
    WHERE region_id = :region_id
    """)
    data = db.execute(q, {"region_id": region_id}).scalar()
    return JSONResponse(
        content=data or [],
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get("/region/{region_id}/boundary.geojson")
def region_boundary_geojson(region_id: str, db: Session = Depends(get_db)):
    """
    Возвращает GeoJSON с границей региона (без деления на районы).
    """
    q = text("""
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', jsonb_build_array(
        jsonb_build_object(
          'type','Feature',
          'properties', jsonb_build_object(
            'id', id::text,
            'name', name
          ),
          'geometry', ST_AsGeoJSON(COALESCE(geom_simplified, geom))::jsonb
        )
      )
    ) AS fc
    FROM regions
    WHERE id = :region_id;
    """)
    return db.execute(q, {"region_id": region_id}).scalar_one()
