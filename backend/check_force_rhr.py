from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверяем, сколько районов имеют валидную геометрию после ST_ForceRHR
result = db.execute(
    text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN ST_IsValid(ST_ForceRHR(ST_MakeValid(geom))) THEN 1 END) as valid_after_force_rhr,
            COUNT(CASE WHEN ST_IsValid(geom) THEN 1 END) as valid_original
        FROM districts
        WHERE region_id = (SELECT id FROM regions WHERE name LIKE '%Свердлов%')
    """)
).fetchone()

print(f"Total districts: {result.total}")
print(f"Valid original: {result.valid_original}")
print(f"Valid after ST_ForceRHR: {result.valid_after_force_rhr}")

# Проверяем районы с проблемами
problematic = db.execute(
    text("""
        SELECT name
        FROM districts
        WHERE region_id = (SELECT id FROM regions WHERE name LIKE '%Свердлов%')
        AND NOT ST_IsValid(ST_ForceRHR(ST_MakeValid(geom)))
    """)
).fetchall()

if problematic:
    print("\nProblematic districts:")
    for p in problematic:
        print(f"  - {p.name}")
else:
    print("\nAll districts are valid after ST_ForceRHR")

db.close()
