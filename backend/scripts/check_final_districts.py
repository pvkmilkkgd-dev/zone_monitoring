"""Check final districts statistics."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN geom IS NOT NULL THEN 1 ELSE 0 END) as with_geom
        FROM districts
    """)).fetchone()
    
    total = result[0]
    with_geom = result[1]
    without_geom = total - with_geom
    pct = with_geom * 100 // total if total > 0 else 0
    
    print("=" * 40)
    print("ITOG ZAGRUZKI GO i MR")
    print("=" * 40)
    print(f"Vsego rayonov: {total}")
    print(f"S geometriej: {with_geom} ({pct}%)")
    print(f"Bez geometrii: {without_geom}")
    print("=" * 40)
