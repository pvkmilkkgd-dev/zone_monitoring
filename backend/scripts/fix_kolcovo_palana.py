import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

fixes = [
    ('городской округ рабочий посёлок Кольцово', 'рабочий посёлок Кольцово'),
    ('городской округ поселок Палана', 'поселок Палана'),
]

with ENGINE.begin() as c:
    for old, new in fixes:
        result = c.execute(text(
            "UPDATE districts SET name = :new WHERE name = :old RETURNING name"
        ), {'new': new, 'old': old})
        for row in result:
            print(f"  {old} -> {new}")

print("Done")
