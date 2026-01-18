from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверяем Свердловскую область
result = db.execute(text("SELECT id, name FROM regions WHERE name LIKE '%Свердлов%'")).fetchall()
print("Найдено регионов:", len(result))
for row in result:
    print(f"ID: {row.id}, Name: {row.name}")
    
    # Проверяем, есть ли геометрия
    geom_check = db.execute(text("SELECT ST_AsText(ST_Envelope(geom)) as bbox FROM regions WHERE id = :id"), {"id": row.id}).fetchone()
    if geom_check and geom_check.bbox:
        print(f"  Геометрия: есть")
        print(f"  BBox: {geom_check.bbox}")
    else:
        print(f"  Геометрия: НЕТ!")

db.close()
