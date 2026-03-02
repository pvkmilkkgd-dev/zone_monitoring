"""Check городские округа in the database."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.connect() as c:
    # Count by type
    types = {
        'городской округ': "name LIKE '%городской округ%'",
        'город ': "name LIKE 'город %' AND name NOT LIKE 'город-курорт%' AND name NOT LIKE '%городской%'",
        'город-курорт': "name LIKE '%город-курорт%'",
        'муниципальный округ': "name LIKE '%муниципальный округ%' OR name LIKE '%Муниципальный округ%'",
        'муниципальный район': "name LIKE '%муниципальный район%' OR name LIKE '%Муниципальный район%'",
        'ЗАТО': "name LIKE '%ЗАТО%'",
    }
    
    for label, where in types.items():
        row = c.execute(text(f"SELECT COUNT(*) FROM districts WHERE {where}")).fetchone()
        print(f"{label}: {row[0]}")
    
    print("\n=== Примеры 'городской округ' ===")
    rows = c.execute(text(
        "SELECT d.name, r.name FROM districts d JOIN regions r ON d.region_id = r.id "
        "WHERE d.name LIKE '%городской округ%' ORDER BY r.name LIMIT 30"
    )).fetchall()
    for dname, rname in rows:
        print(f"  [{rname}] {dname}")
    
    print(f"\n=== Примеры 'город X' (без 'городской округ') ===")
    rows = c.execute(text(
        "SELECT d.name, r.name FROM districts d JOIN regions r ON d.region_id = r.id "
        "WHERE d.name LIKE 'город %' AND d.name NOT LIKE 'город-курорт%' "
        "AND d.name NOT LIKE '%городской%' ORDER BY r.name LIMIT 30"
    )).fetchall()
    for dname, rname in rows:
        print(f"  [{rname}] {dname}")
