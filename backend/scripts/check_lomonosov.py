"""Проверка: Ломоносовский МР в СПб или в Ленобласти?"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    # СПб
    rid_spb = c.execute(text("SELECT id FROM regions WHERE name = 'город Санкт-Петербург'")).scalar()
    spb = c.execute(text("SELECT name FROM districts WHERE region_id = :r ORDER BY name"), {'r': str(rid_spb)}).fetchall()
    print("Санкт-Петербург:", [x[0] for x in spb])
    # Ленобласть
    rid_lo = c.execute(text("SELECT id FROM regions WHERE name = 'Ленинградская область'")).scalar()
    if rid_lo:
        lo = c.execute(text("SELECT name FROM districts WHERE region_id = :r ORDER BY name"), {'r': str(rid_lo)}).fetchall()
        print("Ленинградская область:", [x[0] for x in lo])
    # Где Ломоносовский
    row = c.execute(text("""
        SELECT r.name, d.name, d.id FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name LIKE '%Ломоносов%'
    """)).fetchall()
    print("Записи Ломоносовский:", row)
