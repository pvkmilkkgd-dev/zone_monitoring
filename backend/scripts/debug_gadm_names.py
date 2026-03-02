"""Debug GADM names vs DB names."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings

CACHE_FILE = Path(__file__).parent / "geodata" / "districts_cache" / "gadm_rus_level2.json"

# Load GADM
with open(CACHE_FILE, 'r', encoding='utf-8') as f:
    gadm = json.load(f)

# Get sample GADM features for Altai Krai
print("GADM названия для Алтайского края:")
print("-" * 60)
for feature in gadm.get('features', [])[:50]:
    props = feature.get('properties', {})
    if 'Altay' in props.get('NAME_1', '') or 'Алтай' in props.get('NL_NAME_1', ''):
        print(f"  Region: {props.get('NAME_1')} / {props.get('NL_NAME_1')}")
        print(f"  District: {props.get('NAME_2')} / {props.get('NL_NAME_2')}")
        print()

# Get DB names
print("\nDB названия для Алтайского края:")
print("-" * 60)
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT d.name FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Алтайский край'
        ORDER BY d.name
        LIMIT 10
    """)).fetchall()
    
    for row in result:
        print(f"  {row[0]}")
