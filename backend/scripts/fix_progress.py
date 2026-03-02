import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
with e.begin() as c:
    r = c.execute(text(
        "UPDATE districts SET name = 'городской округ Прогресс' "
        "WHERE name LIKE '%Прогресс%' RETURNING name"
    ))
    for row in r:
        print(f"  {row[0]} -> городской округ Прогресс")
print("Done")
