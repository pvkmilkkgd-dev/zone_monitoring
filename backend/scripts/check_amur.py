"""Проверка: Верхнебуреинский, Константиновский, Селемджинский в Амурской обл. и Хабаровском крае."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    # Верхнебуреинский — где в базе?
    r = c.execute(text("""
        SELECT r.name, d.name, d.id FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name ILIKE '%верхнебуреин%'
    """)).fetchall()
    print("Верхнебуреинский в базе:", r)
    # Константиновский и Селемджинский в Амурской
    rid_amur = c.execute(text("SELECT id FROM regions WHERE name = 'Амурская область'")).scalar()
    r2 = c.execute(text("""
        SELECT name FROM districts WHERE region_id = :rid AND (name ILIKE '%константинов%' OR name ILIKE '%селемджин%')
    """), {'rid': str(rid_amur)}).fetchall()
    print("В Амурской обл. (Константинов/Селемджин):", [x[0] for x in r2])
    # Все районы Амурской
    all_amur = c.execute(text("SELECT name FROM districts WHERE region_id = :rid ORDER BY name"), {'rid': str(rid_amur)}).fetchall()
    print("Всего районов Амурская область:", len(all_amur))
    for x in all_amur:
        print(" ", x[0])
