from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверяем районы с неправильной геометрией (точки или линии)
districts = db.execute(
    text("""
        SELECT 
            name,
            ST_GeometryType(geom) as geom_type,
            ST_NPoints(geom) as num_points,
            ST_XMin(geom) - ST_XMax(geom) as width,
            ST_YMin(geom) - ST_YMax(geom) as height
        FROM districts
        WHERE region_id = (SELECT id FROM regions WHERE name LIKE '%Свердлов%')
        ORDER BY ST_NPoints(geom) ASC
    """)
).fetchall()

print("Rajony s podozritelnoj geometriej (sortirovka po kolichestvu tochek):")
print()

for d in districts:
    width = abs(d.width) if d.width else 0
    height = abs(d.height) if d.height else 0
    
    # Если район имеет очень мало точек или очень маленький размер - это проблема
    if d.num_points < 20 or width < 0.01 or height < 0.01:
        print(f"[PROBLEM] {d.name}:")
        print(f"  Type: {d.geom_type}")
        print(f"  Points: {d.num_points}")
        print(f"  Size: {width:.6f}° x {height:.6f}°")
        print()

db.close()
