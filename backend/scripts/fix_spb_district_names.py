"""
Санкт-Петербург: не муниципальные районы, а районы города федерального значения.
Замена: «X муниципальный район» → «X район» для всех 18 районов СПб.
"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.begin() as c:
    # Заменить " муниципальный район" на " район" у всех районов региона СПб
    r = c.execute(text("""
        UPDATE districts d SET name = REPLACE(d.name, ' муниципальный район', ' район')
        FROM regions r
        WHERE d.region_id = r.id AND r.name = 'город Санкт-Петербург' AND d.name LIKE '%муниципальный район'
        RETURNING d.name
    """))
    updated = list(r)
    print(f"Переименовано: {len(updated)} записей")

with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'город Санкт-Петербург' ORDER BY d.name
    """)).fetchall()
    print("Названия после правки (первые 5 и последние 2):")
    for r in rows[:5]:
        print(" ", r[0])
    print(" ...")
    for r in rows[-2:]:
        print(" ", r[0])
