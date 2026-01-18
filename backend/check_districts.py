from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Получаем ID Свердловской области
region_result = db.execute(text("SELECT id, name FROM regions WHERE name LIKE '%Свердлов%'")).fetchone()
if region_result:
    region_id = region_result.id
    region_name = region_result.name
    print(f"Регион: {region_name} (ID: {region_id})")
    print()
    
    # Проверяем, есть ли районы
    districts = db.execute(
        text("SELECT id, name, region_id FROM districts WHERE region_id = :region_id ORDER BY name"),
        {"region_id": region_id}
    ).fetchall()
    
    print(f"Найдено районов: {len(districts)}")
    print()
    
    if districts:
        print("Список районов:")
        for d in districts:
            # Проверяем геометрию
            geom_check = db.execute(
                text("SELECT ST_IsValid(geom) as valid, ST_GeometryType(geom) as type FROM districts WHERE id = :id"),
                {"id": d.id}
            ).fetchone()
            
            status = "✓" if geom_check and geom_check.valid else "✗"
            geom_type = geom_check.type if geom_check else "N/A"
            print(f"  {status} {d.name} ({geom_type})")
    else:
        print("Районы не найдены в БД!")
else:
    print("Свердловская область не найдена в БД")

db.close()
