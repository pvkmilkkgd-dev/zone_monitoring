from app.db.session import SessionLocal
from sqlalchemy import text
import json

db = SessionLocal()

# Ищем ГО Верх-Нейвинский
district = db.execute(
    text("""
        SELECT 
            name,
            ST_AsGeoJSON(geom)::json as geom_json,
            ST_NRings(geom) as num_rings
        FROM districts 
        WHERE name LIKE '%Верх-Нейв%'
    """)
).fetchone()

if district:
    print(f"Rajon: {district.name}")
    print(f"Kolichestvo kolets: {district.num_rings}")
    geom = district.geom_json
    print(f"Tip: {geom['type']}")
    print(f"Kolichestvo poligonov: {len(geom['coordinates'])}")
    if len(geom['coordinates']) > 0:
        print(f"Kolichestvo kolets v pervom poligone: {len(geom['coordinates'][0])}")

db.close()
