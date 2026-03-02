import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT d.name 
        FROM districts d
        JOIN regions r ON r.id = d.region_id
        WHERE r.name = 'Алтайский край'
        ORDER BY d.name
    """)).fetchall()

print(f"Алтайский край: {len(rows)} districts\n")
for i, (name,) in enumerate(rows, 1):
    print(f"  {i:3d}. {name}")
