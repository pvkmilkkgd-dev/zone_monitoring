"""Проверка названий районов Санкт-Петербурга в базе."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rid = c.execute(text("SELECT id FROM regions WHERE name = 'город Санкт-Петербург'")).scalar()
    rows = c.execute(text("SELECT d.name FROM districts d WHERE d.region_id = :rid ORDER BY d.name"), {'rid': str(rid)}).fetchall()
    print("Текущие названия районов СПб в базе:")
    for r in rows:
        print(" ", r[0])
