"""Verify names after ОКТМО update"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)

with e.connect() as c:
    for region in ['Белгородская область', 'Архангельская область', 'Свердловская область',
                   'Алтайский край', 'Челябинская область']:
        rows = c.execute(text("""
            SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :name ORDER BY d.name LIMIT 8
        """), {'name': region}).fetchall()
        print(f"\n{region}:")
        for r in rows:
            print(f"  {r[0]}")
