"""Check districts detail."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Districts without geometry by region
    print("Районы БЕЗ геометрии по регионам:")
    print("-" * 60)
    
    result = conn.execute(text("""
        SELECT r.name as region_name, COUNT(d.id) as count
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.geom IS NULL
        GROUP BY r.name
        ORDER BY count DESC
        LIMIT 20
    """)).fetchall()
    
    total_missing = 0
    for row in result:
        print(f"  {row[0]}: {row[1]} районов без геометрии")
        total_missing += row[1]
    
    print(f"\nВсего регионов с отсутствующей геометрией районов: {len(result)}")
    
    # Sample districts without geometry
    print("\nПримеры районов без геометрии:")
    result = conn.execute(text("""
        SELECT d.name, r.name as region_name
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.geom IS NULL
        ORDER BY r.name, d.name
        LIMIT 15
    """)).fetchall()
    
    for row in result:
        print(f"  {row[1]} -> {row[0]}")
