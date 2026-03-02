import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rows = c.execute(text("SELECT name FROM regions ORDER BY name")).fetchall()
    for r in rows:
        n = r[0].lower()
        if any(x in n for x in ['москв', 'петерб', 'севастоп', 'город']):
            print(r[0])
    print(f"\nTotal regions: {len(rows)}")
