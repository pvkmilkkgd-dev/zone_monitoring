"""Check Donetsk data structure."""
import json
from pathlib import Path

cache_file = Path(__file__).parent / "geodata" / "osm_region_5765844.json"
with open(cache_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

elements = data.get('elements', [])
print(f'Elements: {len(elements)}')

if elements:
    rel = elements[0]
    print(f'Type: {rel.get("type")}')
    members = rel.get('members', [])
    print(f'Members: {len(members)}')
    
    # Count types and roles
    types = {}
    roles = {}
    for m in members:
        t = m.get('type')
        r = m.get('role', 'empty')
        types[t] = types.get(t, 0) + 1
        roles[r] = roles.get(r, 0) + 1
    
    print(f'Types: {types}')
    print(f'Roles: {roles}')
    
    # Check geometry
    with_geom = sum(1 for m in members if m.get('geometry'))
    print(f'With geometry: {with_geom}')
    
    # Check way geometries
    ways_with_coords = 0
    total_coords = 0
    for m in members:
        if m.get('type') == 'way':
            geom = m.get('geometry', [])
            if geom:
                ways_with_coords += 1
                total_coords += len(geom)
    
    print(f'Ways with coords: {ways_with_coords}')
    print(f'Total coords: {total_coords}')
