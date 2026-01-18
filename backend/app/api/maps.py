from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db  # ВАЖНО: app., не backend.app.

router = APIRouter(prefix="/maps/ru", tags=["maps"])


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
          'geometry', ST_AsGeoJSON(COALESCE(geom_simplified, geom))::jsonb
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
        # Если есть районы для региона, выбираем их
        q = text("""
        SELECT jsonb_build_object(
          'type','FeatureCollection',
          'features', COALESCE(jsonb_agg(
            jsonb_build_object(
              'type','Feature',
              'properties', jsonb_build_object(
                'id', id::text,
                'name', name
              ),
              'geometry', ST_AsGeoJSON(ST_ForceRHR(ST_MakeValid(geom)))::jsonb
            )
          ), '[]'::jsonb)
        ) AS fc
        FROM districts
        WHERE region_id = :region_id;
        """)
        return db.execute(q, {"region_id": region_id}).scalar_one()
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
