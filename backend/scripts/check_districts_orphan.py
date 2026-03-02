"""Check orphan districts (without region)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Districts without matching region
    print("Районы без связи с регионом:")
    result = conn.execute(text("""
        SELECT d.name, d.region_id, d.geom IS NOT NULL as has_geom
        FROM districts d
        LEFT JOIN regions r ON d.region_id = r.id
        WHERE r.id IS NULL
        LIMIT 20
    """)).fetchall()
    
    for row in result:
        print(f"  {row[0]} (region_id: {row[1]}, geom: {row[2]})")
    
    print(f"\nВсего orphan: {len(result)}")
    
    # Districts with NULL geometry (with region)
    print("\nРайоны С регионом, но БЕЗ геометрии:")
    result = conn.execute(text("""
        SELECT d.name, r.name as region_name
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.geom IS NULL
        LIMIT 20
    """)).fetchall()
    
    for row in result:
        print(f"  {row[1]} -> {row[0]}")
    
    print(f"\nВсего: {len(result)}")
    
    # Count by geometry status
    print("\n\nСтатистика:")
    result = conn.execute(text("""
        SELECT 
            CASE 
                WHEN r.id IS NULL THEN 'orphan'
                WHEN d.geom IS NULL THEN 'no_geom'
                ELSE 'ok'
            END as status,
            COUNT(*) as cnt
        FROM districts d
        LEFT JOIN regions r ON d.region_id = r.id
        GROUP BY 1
    """)).fetchall()
    
    for row in result:
        print(f"  {row[0]}: {row[1]}")
