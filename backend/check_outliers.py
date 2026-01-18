from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверяем районы с подозрительно большим размером
districts = db.execute(
    text("""
        SELECT 
            name,
            ST_XMax(geom) - ST_XMin(geom) as width,
            ST_YMax(geom) - ST_YMin(geom) as height,
            ST_XMin(geom) as min_lon,
            ST_YMin(geom) as min_lat,
            ST_XMax(geom) as max_lon,
            ST_YMax(geom) as max_lat
        FROM districts 
        WHERE region_id = (SELECT id FROM regions WHERE name LIKE '%Свердлов%')
        ORDER BY (ST_XMax(geom) - ST_XMin(geom)) DESC
        LIMIT 10
    """)
).fetchall()

print("Top 10 samyh shirokikh rajonov:")
for d in districts:
    print(f"{d.name}: {d.width:.2f}° x {d.height:.2f}°")
    print(f"  Bbox: [{d.min_lon:.2f}, {d.min_lat:.2f}] - [{d.max_lon:.2f}, {d.max_lat:.2f}]")
    
    # Проверяем, не выходят ли координаты за пределы Свердловской области
    if d.min_lon < 56 or d.max_lon > 67 or d.min_lat < 55 or d.max_lat > 62:
        print(f"  WARNING: Koordinaty vne oblasty Sverdlovskoj oblasti!")

db.close()
