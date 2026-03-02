import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rid = c.execute(text("SELECT id FROM regions WHERE name = 'город Москва'")).scalar()
    rows = c.execute(text("SELECT name FROM districts WHERE region_id = :rid ORDER BY name"), {'rid': str(rid)}).fetchall()
    for r in rows:
        print(r[0])
