"""Fix districts where settlement type is used instead of MO name."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

# Based on research:
# 1. "рабочий поселок Кольцово" (Новосибирская) -> "городской округ рабочий посёлок Кольцово"
#    (ОКТМО code 50740000, official name includes "рабочий посёлок" as part of ГО name)
# 2. "рабочий поселок Новогуровский" (Тульская) -> "городской округ Новогуровский"
# 3. "поселок Палана" (Камчатский) -> "городской округ поселок Палана"
# 4. "поселение Московский" (Москва) -> keep as-is (internal Moscow structure)
# 5. "Бежтинский участок" (Дагестан) -> keep as-is (unique administrative unit)

fixes = [
    ('%рабочий поселок Кольцово%', 'городской округ рабочий посёлок Кольцово'),
    ('%рабочий поселок Новогуровский%', 'городской округ Новогуровский'),
    ('поселок Палана', 'городской округ поселок Палана'),
]

with ENGINE.begin() as c:
    for pattern, new_name in fixes:
        result = c.execute(text(
            "UPDATE districts SET name = :new WHERE name LIKE :p RETURNING name"
        ), {'new': new_name, 'p': pattern})
        for row in result:
            print(f"  {row[0]} -> {new_name}")

# Verify
print("\nПроверка оставшихся необычных:")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, r.name FROM districts d 
        JOIN regions r ON d.region_id = r.id 
        WHERE d.name NOT LIKE '%%муниципальный%%'
        AND d.name NOT LIKE '%%Муниципальный%%'
        AND d.name NOT LIKE '%%городской%%'
        AND d.name NOT LIKE '%%город %%'
        AND d.name NOT LIKE '%%город-курорт%%'
        AND d.name NOT LIKE '%%ЗАТО%%'
        AND d.name NOT LIKE '%%район%%'
        AND d.name NOT LIKE '%%округ%%'
        AND d.name NOT LIKE '%%административный%%'
        ORDER BY r.name
    """)).fetchall()
    print(f"  {len(rows)} шт:")
    for dname, rname in rows:
        print(f"  [{rname}] {dname}")

print("\nDone!")
