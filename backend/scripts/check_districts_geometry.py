"""Check districts geometry status."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Count districts with and without geometry
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN geom IS NOT NULL THEN 1 ELSE 0 END) as with_geom,
            SUM(CASE WHEN geom IS NULL THEN 1 ELSE 0 END) as without_geom
        FROM districts
    """)).fetchone()
    
    print(f"Всего районов: {result[0]}")
    print(f"С геометрией: {result[1]}")
    print(f"Без геометрии: {result[2]}")
    
    # Show sample districts by region
    print("\nПример районов по регионам:")
    result = conn.execute(text("""
        SELECT r.name as region_name, 
               COUNT(d.id) as district_count,
               SUM(CASE WHEN d.geom IS NOT NULL THEN 1 ELSE 0 END) as with_geom
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        GROUP BY r.name
        ORDER BY r.name
        LIMIT 10
    """)).fetchall()
    
    for row in result:
        print(f"  {row[0]}: {row[1]} районов, {row[2]} с геометрией")
