from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Получаем ID Свердловской области
region_result = db.execute(text("SELECT id, name FROM regions WHERE name LIKE '%Свердлов%'")).fetchone()
if region_result:
    region_id = region_result.id
    
    # Проверяем геометрию первых нескольких районов
    districts = db.execute(
        text("""
            SELECT 
                id, 
                name,
                ST_GeometryType(geom) as geom_type,
                ST_NPoints(geom) as num_points,
                ST_IsValid(geom) as is_valid,
                ST_AsText(ST_Envelope(geom)) as bbox
            FROM districts 
            WHERE region_id = :region_id 
            LIMIT 5
        """),
        {"region_id": region_id}
    ).fetchall()
    
    print("Проверка геометрии районов:")
    print()
    
    for d in districts:
        print(f"Район: {d.name}")
        print(f"  Тип геометрии: {d.geom_type}")
        print(f"  Количество точек: {d.num_points}")
        print(f"  Валидность: {d.is_valid}")
        print(f"  BBox: {d.bbox[:100]}...")
        print()

db.close()
