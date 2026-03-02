"""Проверка районов Севастополя в базе."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rid = c.execute(text("SELECT id FROM regions WHERE name = 'город Севастополь'")).scalar()
    if not rid:
        print("Регион город Севастополь не найден")
    else:
        rows = c.execute(text("SELECT d.id, d.name, ST_NPoints(d.geom) as pts FROM districts d WHERE d.region_id = :rid ORDER BY d.name"), {'rid': str(rid)}).fetchall()
        print("Сейчас в базе (город Севастополь):")
        for r in rows:
            print(f"  {r[1]}  (pts={r[2]})")
