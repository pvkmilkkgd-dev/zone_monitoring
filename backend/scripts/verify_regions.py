"""Verify all regions have correct geometry."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT name, ROUND(ST_Area(geom::geography) / 1000000) as area_km2
        FROM regions
        WHERE name IN (
            'Республика Крым',
            'город Севастополь', 
            'Донецкая Народная Республика',
            'Луганская Народная Республика',
            'Запорожская область',
            'Херсонская область'
        )
        ORDER BY name
    """)).fetchall()
    
    print("Проверка исправленных регионов:")
    print("-" * 50)
    for row in result:
        print(f"  {row[0]}: {row[1]} km2")
