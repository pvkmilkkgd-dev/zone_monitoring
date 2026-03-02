import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.begin() as c:
    r = c.execute(text("UPDATE districts SET name = 'Заполярный муниципальный район' WHERE name = 'Заполярный район'"))
    print(f"Fixed: {r.rowcount}")
