"""Check North Ossetia name."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT name FROM regions WHERE name LIKE '%Осетия%'")).fetchall()
    for row in result:
        name = row[0]
        # Show character codes for dash
        for i, c in enumerate(name):
            if c in '-—–':
                print(f"Position {i}: char '{c}' code {ord(c)}")
        print(f"DB: '{name}'")
        print(f"Repr: {repr(name)}")
