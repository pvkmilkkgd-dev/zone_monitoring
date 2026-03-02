import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

# The large one (4309 km2) is the муниципальный округ, not the city
# id=5811251b - 4309 km2 -> "Гусь-Хрустальный муниципальный округ"
with ENGINE.begin() as c:
    result = c.execute(text("""
        UPDATE districts SET name = 'Гусь-Хрустальный муниципальный округ'
        WHERE id = '5811251b-f75c-411a-bb1b-aee3e895ce61'
        RETURNING name
    """))
    for row in result:
        print(f"  Fixed: -> {row[0]}")

    # Also noticed "округ Муром" in ОКТМО and "Покров" without type
    # Let's check current state of Murom
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Владимирская область' AND d.name LIKE '%Муром%'
    """)).fetchall()
    for row in rows:
        print(f"  Murom: {row[0]}")

# Verify
print("\nВладимирская область после исправления:")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Владимирская область' ORDER BY d.name
    """)).fetchall()
    for row in rows:
        print(f"  {row[0]}")

print("Done")
