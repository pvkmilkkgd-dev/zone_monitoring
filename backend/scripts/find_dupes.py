import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, r.name, COUNT(*) as cnt
        FROM districts d JOIN regions r ON d.region_id = r.id
        GROUP BY d.name, r.name
        HAVING COUNT(*) > 1
        ORDER BY r.name, d.name
    """)).fetchall()
    
    if rows:
        print(f"Дубликаты ({len(rows)}):")
        for dname, rname, cnt in rows:
            print(f"  [{rname}] {dname} x{cnt}")
    else:
        print("Дубликатов нет!")
