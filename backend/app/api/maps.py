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
