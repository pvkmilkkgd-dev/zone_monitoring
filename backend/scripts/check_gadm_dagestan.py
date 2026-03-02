# -*- coding: utf-8 -*-
"""Посмотреть что есть в GADM для Дагестана."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

GADM_CACHE = r'c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm_russia_level2.json'

with open(GADM_CACHE, 'r', encoding='utf-8') as f:
    gadm = json.load(f)

dag_features = []
for feat in gadm.get('features', []):
    props = feat.get('properties', {})
    r1 = props.get('NAME_1', '')
    if 'Dagestan' in r1 or 'Дагестан' in r1:
        dag_features.append(feat)

print(f"GADM features for Dagestan: {len(dag_features)}\n")
for f in sorted(dag_features, key=lambda x: x['properties'].get('NAME_2', '')):
    p = f['properties']
    gtype = f.get('geometry', {}).get('type', '?')
    print(f"  NAME_2: {p.get('NAME_2', ''):40s}  NL_NAME_2: {p.get('NL_NAME_2', ''):45s}  type={gtype}")
