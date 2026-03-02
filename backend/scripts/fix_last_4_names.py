"""Fix the last 4 districts with short names manually."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

# Manual fixes based on known official names
fixes = {
    'Черкесский': 'Черкесский городской округ',
    'Карачаевский': 'Карачаевский городской округ',
    'Комаровский': 'ЗАТО Комаровский',
    'Заводоуковский': 'Заводоуковский городской округ',
}

with e.begin() as c:
    for old, new in fixes.items():
        result = c.execute(text("UPDATE districts SET name = :new WHERE name = :old"),
                          {'new': new, 'old': old})
        print(f"  {old} -> {new} ({result.rowcount} updated)")

print("\nDone!")
