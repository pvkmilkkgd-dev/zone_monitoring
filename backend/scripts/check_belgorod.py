"""Проверка: Алексеевский, Валуйский, Шебекинский в Белгородской области."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rid = c.execute(text("SELECT id FROM regions WHERE name = 'Белгородская область'")).scalar()
    if not rid:
        print("Белгородская область не найдена")
    else:
        rows = c.execute(text("""
            SELECT d.name FROM districts d
            WHERE d.region_id = :rid ORDER BY d.name
        """), {'rid': str(rid)}).fetchall()
        print("Белгородская область, все районы:")
        for r in rows:
            print(" ", r[0])
        # Ищем Алексеев, Валуй, Шебекин
        for part in ["Алексеев", "Валуй", "Шебекин"]:
            match = [r[0] for r in rows if part in r[0]]
            print(f"\n  Содержит '{part}': {match}")
