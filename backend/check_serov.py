from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверяем Серовский ГО
district = db.execute(
    text("""
        SELECT 
            name,
            ST_NPoints(geom) as num_points,
            ST_Area(geom) as area,
            ST_XMin(geom) as min_lon,
            ST_YMin(geom) as min_lat,
            ST_XMax(geom) as max_lon,
            ST_YMax(geom) as max_lat
        FROM districts 
        WHERE name LIKE '%Серов%'
    """)
).fetchone()

if district:
    print(f"Rajon: {district.name}")
    print(f"Tochek: {district.num_points}")
    print(f"Ploshad: {district.area:.6f}")
    print(f"Bbox: [{district.min_lon:.2f}, {district.min_lat:.2f}] - [{district.max_lon:.2f}, {district.max_lat:.2f}]")
    width = district.max_lon - district.min_lon
    height = district.max_lat - district.min_lat
    print(f"Razmer: {width:.2f}° x {height:.2f}°")

# Проверим средний размер остальных районов
avg = db.execute(
    text("""
        SELECT 
            AVG(ST_XMax(geom) - ST_XMin(geom)) as avg_width,
            AVG(ST_YMax(geom) - ST_YMin(geom)) as avg_height,
            AVG(ST_Area(geom)) as avg_area
        FROM districts 
        WHERE region_id = (SELECT id FROM regions WHERE name LIKE '%Свердлов%')
    """)
).fetchone()

print()
print(f"Srednij rajon:")
print(f"  Razmer: {avg.avg_width:.2f}° x {avg.avg_height:.2f}°")
print(f"  Ploshad: {avg.avg_area:.6f}")

db.close()
