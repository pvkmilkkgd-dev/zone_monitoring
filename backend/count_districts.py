from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Получаем ID Свердловской области
region_result = db.execute(text("SELECT id, name FROM regions WHERE name LIKE '%Свердлов%'")).fetchone()
if region_result:
    region_id = region_result.id
    
    # Считаем районы
    count = db.execute(
        text("SELECT COUNT(*) FROM districts WHERE region_id = :region_id"),
        {"region_id": region_id}
    ).scalar()
    
    print(f"Rajonov v BD: {count}")

db.close()
