# -*- coding: utf-8 -*-
"""Посмотреть что есть в GADM для Чукотки и что в БД."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm_russia_level2.json'

with open(GADM_CACHE, 'r', encoding='utf-8') as f:
    gadm = json.load(f)

chuk_features = []
for feat in gadm.get('features', []):
    props = feat.get('properties', {})
    r1 = props.get('NAME_1', '')
    if 'Chukot' in r1 or 'Чукот' in r1:
        chuk_features.append(feat)

print(f"GADM features for Chukotka: {len(chuk_features)}\n")
for f in sorted(chuk_features, key=lambda x: x['properties'].get('NAME_2', '')):
    p = f['properties']
    gtype = f.get('geometry', {}).get('type', '?')
    print(f"  NAME_1: {p.get('NAME_1', ''):30s}  NAME_2: {p.get('NAME_2', ''):40s}  NL_NAME_2: {p.get('NL_NAME_2', ''):40s}  type={gtype}")

print()
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name ILIKE '%Чукот%' ORDER BY d.name
    """)).fetchall()
    print(f"DB districts: {len(rows)}")
    for r in rows:
        print(f"  {r[0]}")
