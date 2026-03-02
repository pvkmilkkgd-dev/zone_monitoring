"""
По результатам перепроверки:
1. Верхнебуреинский район — Хабаровский край, не Амурская область. Удалить из Амурской.
2. Константиновский МР (Амурская) → Константиновский муниципальный округ.
3. Селемджинский МР (Амурская) → Селемджинский муниципальный округ.
"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.begin() as c:
    # 1. Удалить Верхнебуреинский район из Амурской области
    r = c.execute(text("""
        DELETE FROM districts d
        USING regions r
        WHERE d.region_id = r.id AND r.name = 'Амурская область' AND d.name = 'Верхнебуреинский район'
        RETURNING d.id
    """))
    deleted = list(r)
    print("1. Удалён из Амурской области: Верхнебуреинский район —", "да" if deleted else "не найден")

    # 2. Константиновский муниципальный район → Константиновский муниципальный округ
    c.execute(text("""
        UPDATE districts d SET name = 'Константиновский муниципальный округ'
        FROM regions r WHERE d.region_id = r.id AND r.name = 'Амурская область'
        AND d.name = 'Константиновский муниципальный район'
    """))
    print("2. Заменено: Константиновский муниципальный район → Константиновский муниципальный округ")

    # 3. Селемджинский муниципальный район → Селемджинский муниципальный округ
    c.execute(text("""
        UPDATE districts d SET name = 'Селемджинский муниципальный округ'
        FROM regions r WHERE d.region_id = r.id AND r.name = 'Амурская область'
        AND d.name = 'Селемджинский муниципальный район'
    """))
    print("3. Заменено: Селемджинский муниципальный район → Селемджинский муниципальный округ")

# Проверка
with ENGINE.connect() as c:
    amur = c.execute(text("""
        SELECT d.name FROM districts d
        JOIN regions r ON d.region_id = r.id WHERE r.name = 'Амурская область'
        ORDER BY d.name
    """)).fetchall()
    print("\nАмурская область после правок (фрагмент):")
    for row in amur:
        if "Верхнебуреин" in row[0] or "Константинов" in row[0] or "Селемджин" in row[0]:
            print(" ", row[0])
    upper = [row[0] for row in amur if "Верхнебуреин" in row[0]]
    print("  Записей Верхнебуреинский в Амурской:", len(upper))
    khab = c.execute(text("""
        SELECT COUNT(*) FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Хабаровский край' AND d.name ILIKE '%верхнебуреин%'
    """)).scalar()
    print("  Верхнебуреинский в Хабаровском крае:", khab)
