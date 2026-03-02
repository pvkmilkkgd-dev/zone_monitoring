"""Check and regenerate regions GeoJSON from database."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

GEOJSON_PATH = Path(__file__).parent.parent / "maps" / "ru" / "regions.geojson"


def check_current():
    """Check current GeoJSON file."""
    if not GEOJSON_PATH.exists():
        print("GeoJSON file not found")
        return
    
    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Type: {data.get('type')}")
    print(f"Features count: {len(data.get('features', []))}")
    
    if data.get('features'):
        f = data['features'][0]
        props = f.get('properties', {})
        print(f"First feature properties: {list(props.keys())}")
        print(f"First feature name: {props.get('name')}")


def regenerate_geojson():
    """Regenerate GeoJSON from database."""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                id,
                name,
                code,
                ST_AsGeoJSON(geom)::json as geometry
            FROM regions
            WHERE geom IS NOT NULL
            ORDER BY name
        """)).fetchall()
        
        features = []
        for row in result:
            feature = {
                "type": "Feature",
                "properties": {
                    "id": str(row[0]),
                    "name": row[1],
                    "code": row[2]
                },
                "geometry": row[3]
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Ensure directory exists
        GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(GEOJSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        
        print(f"Generated GeoJSON with {len(features)} regions")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "regenerate":
        regenerate_geojson()
    else:
        check_current()
