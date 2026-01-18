from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Получаем общий bounding box для всех районов Свердловской области
result = db.execute(
    text("""
        SELECT 
            ST_XMin(ST_Extent(geom)) as min_lon,
            ST_YMin(ST_Extent(geom)) as min_lat,
            ST_XMax(ST_Extent(geom)) as max_lon,
            ST_YMax(ST_Extent(geom)) as max_lat
        FROM districts
        WHERE region_id = (SELECT id FROM regions WHERE name LIKE '%Свердлов%')
    """)
).fetchone()

if result:
    min_lon, min_lat, max_lon, max_lat = result
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2
    width = max_lon - min_lon
    height = max_lat - min_lat
    
    print(f"Bounding Box:")
    print(f"  Min: [{min_lon:.2f}, {min_lat:.2f}]")
    print(f"  Max: [{max_lon:.2f}, {max_lat:.2f}]")
    print(f"  Razmer: {width:.2f}° x {height:.2f}°")
    print()
    print(f"Rekomendovannye nastroyki:")
    print(f"  center: [{center_lon:.2f}, {center_lat:.2f}]")
    print(f"  scale: {int(160000 / max(width, height))}")

db.close()
