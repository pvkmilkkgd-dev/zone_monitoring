import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    rows = conn.execute(text(
        "SELECT id, name FROM districts WHERE name LIKE 'городской округ город %'"
    )).fetchall()
    
    print(f"Found {len(rows)} entries to rename:\n")
    for did, name in rows:
        new_name = name.replace("городской округ город ", "городской округ ")
        print(f"  '{name}' -> '{new_name}'")
        conn.execute(text("UPDATE districts SET name = :name WHERE id = :id"),
                    {"name": new_name, "id": str(did)})
    
    conn.commit()
    print(f"\nDone!")
