"""
Reload Sverdlovsk Oblast districts from OpenStreetMap via Overpass API.
Downloads ALL administrative boundaries within the oblast at once.
"""
import sys
import json
import time
import requests
from uuid import uuid4

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

# Official list of Sverdlovsk Oblast administrative-territorial units
# Source: Wikipedia + Zakon "Ob administrativno-territorialnom ustroystve Sverdlovskoy oblasti"
OFFICIAL_DISTRICTS = [
    # 30 rayonov
    "Алапаевский район",
    "Артёмовский район",
    "Артинский район",
    "Ачитский район",
    "Байкаловский район",
    "Белоярский район",
    "Богдановичский район",
    "Верхнесалдинский район",
    "Верхотурский район",
    "Гаринский район",
    "Ирбитский район",
    "Каменский район",
    "Камышловский район",
    "Красноуфимский район",
    "Невьянский район",
    "Нижнесергинский район",
    "Новолялинский район",
    "Пригородный район",
    "Пышминский район",
    "Режевский район",
    "Серовский район",
    "Слободо-Туринский район",
    "Сухоложский район",
    "Сысертский район",
    "Таборинский район",
    "Тавдинский район",
    "Талицкий район",
    "Тугулымский район",
    "Туринский район",
    "Шалинский район",
    # 25 gorodov oblastnogo znacheniya
    "город Алапаевск",
    "город Асбест",
    "город Берёзовский",
    "город Верхняя Пышма",
    "город Екатеринбург",
    "город Заречный",
    "город Ивдель",
    "город Ирбит",
    "город Каменск-Уральский",
    "город Камышлов",
    "город Карпинск",
    "город Качканар",
    "город Кировград",
    "город Краснотурьинск",
    "город Красноуральск",
    "город Красноуфимск",
    "город Кушва",
    "город Нижний Тагил",
    "город Нижняя Салда",
    "город Нижняя Тура",
    "город Первоуральск",
    "город Полевской",
    "город Ревда",
    "город Североуральск",
    "город Серов",
    # 4 ZATO
    "ЗАТО город Лесной",
    "ЗАТО город Новоуральск",
    "ЗАТО посёлок Свободный",
    "ЗАТО посёлок Уральский",
]


def download_osm_boundaries():
    """Download all admin boundaries within Sverdlovsk Oblast from Overpass."""
    print("Downloading boundaries from OpenStreetMap...")
    
    # Query: all admin_level=5,6 relations within Sverdlovsk Oblast (relation 79379)
    query = """
[out:json][timeout:120];
area["name"="Свердловская область"]["admin_level"="4"]->.region;
(
  relation["boundary"="administrative"]["admin_level"~"^(5|6)$"](area.region);
);
out body;
>;
out skel qt;
"""
    
    url = "https://overpass-api.de/api/interpreter"
    resp = requests.post(url, data={'data': query}, timeout=180)
    
    if resp.status_code != 200:
        print(f"Overpass error: {resp.status_code}")
        return None
    
    data = resp.json()
    elements = data.get('elements', [])
    
    # Separate relations, ways, nodes
    relations = [e for e in elements if e['type'] == 'relation']
    ways_dict = {e['id']: e for e in elements if e['type'] == 'way'}
    nodes_dict = {e['id']: e for e in elements if e['type'] == 'node'}
    
    print(f"  Relations: {len(relations)}")
    print(f"  Ways: {len(ways_dict)}")
    print(f"  Nodes: {len(nodes_dict)}")
    
    return relations, ways_dict, nodes_dict


def build_polygon_from_relation(relation, ways_dict, nodes_dict):
    """Build GeoJSON polygon from OSM relation."""
    outer_rings = []
    inner_rings = []
    
    for member in relation.get('members', []):
        if member['type'] != 'way':
            continue
        
        way_id = member['ref']
        way = ways_dict.get(way_id)
        if not way:
            continue
        
        coords = []
        for nd_ref in way.get('nodes', []):
            node = nodes_dict.get(nd_ref)
            if node:
                coords.append([node['lon'], node['lat']])
        
        if not coords:
            continue
        
        if member.get('role') == 'inner':
            inner_rings.append(coords)
        else:
            outer_rings.append(coords)
    
    if not outer_rings:
        return None
    
    # Merge outer ways into closed rings
    merged = merge_ways(outer_rings)
    
    if not merged:
        return None
    
    # Build GeoJSON
    if len(merged) == 1:
        ring = merged[0]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        
        polygon = [ring]
        # Add inner rings
        for inner in inner_rings:
            if inner[0] != inner[-1]:
                inner.append(inner[0])
            polygon.append(inner)
        
        return {'type': 'Polygon', 'coordinates': polygon}
    else:
        # MultiPolygon
        polygons = []
        for ring in merged:
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            polygons.append([ring])
        return {'type': 'MultiPolygon', 'coordinates': polygons}


def merge_ways(ways):
    """Merge ways into closed rings."""
    if not ways:
        return []
    
    rings = []
    remaining = list(ways)
    
    while remaining:
        current = list(remaining.pop(0))
        changed = True
        
        while changed:
            changed = False
            for i, way in enumerate(remaining):
                if not way:
                    continue
                
                # Try to connect
                if current[-1] == way[0]:
                    current.extend(way[1:])
                    remaining.pop(i)
                    changed = True
                    break
                elif current[-1] == way[-1]:
                    current.extend(reversed(way[:-1]))
                    remaining.pop(i)
                    changed = True
                    break
                elif current[0] == way[-1]:
                    current = way[:-1] + current
                    remaining.pop(i)
                    changed = True
                    break
                elif current[0] == way[0]:
                    current = list(reversed(way[1:])) + current
                    remaining.pop(i)
                    changed = True
                    break
        
        # Close the ring if needed
        if len(current) > 2:
            rings.append(current)
    
    return rings


def normalize(name):
    """Normalize name for matching."""
    n = name.lower().strip()
    n = n.replace('ё', 'е')
    n = n.replace('-', ' ').replace('—', ' ')
    # Remove common prefixes/suffixes
    for w in ['город ', 'зато ', 'поселок ', 'посёлок ', 'район', 'городской округ', 'муниципальный округ']:
        n = n.replace(w, '')
    return ' '.join(n.split()).strip()


def match_osm_to_official(osm_name, official_list):
    """Find best match between OSM name and official list."""
    osm_norm = normalize(osm_name)
    
    best_match = None
    best_score = 0
    
    for official in official_list:
        off_norm = normalize(official)
        
        # Exact match
        if osm_norm == off_norm:
            return official
        
        # One contains the other
        if osm_norm in off_norm or off_norm in osm_norm:
            score = min(len(osm_norm), len(off_norm)) / max(len(osm_norm), len(off_norm))
            if score > best_score:
                best_score = score
                best_match = official
        
        # First word match
        osm_words = osm_norm.split()
        off_words = off_norm.split()
        if osm_words and off_words and osm_words[0] == off_words[0] and len(osm_words[0]) > 3:
            score = 0.8
            if score > best_score:
                best_score = score
                best_match = official
    
    return best_match if best_score > 0.5 else None


def main():
    print("=" * 60)
    print("Reload Sverdlovsk Oblast districts from OSM")
    print(f"Official count: {len(OFFICIAL_DISTRICTS)}")
    print("=" * 60)
    
    # Download from OSM
    result = download_osm_boundaries()
    if not result:
        print("Failed to download!")
        return
    
    relations, ways_dict, nodes_dict = result
    
    # Build features
    features = []
    for rel in relations:
        tags = rel.get('tags', {})
        name = tags.get('name', '')
        admin_level = tags.get('admin_level', '')
        
        if not name:
            continue
        
        geojson = build_polygon_from_relation(rel, ways_dict, nodes_dict)
        if not geojson:
            print(f"  Skip (no geometry): {name}")
            continue
        
        features.append({
            'name': name,
            'admin_level': admin_level,
            'geometry': geojson,
            'osm_id': rel['id'],
        })
    
    print(f"\nBuilt {len(features)} features with geometry")
    print("\nOSM names:")
    for f in sorted(features, key=lambda x: x['name']):
        print(f"  [{f['admin_level']}] {f['name']}")
    
    # Connect to DB
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Get region ID
        region = conn.execute(text(
            "SELECT id FROM regions WHERE name LIKE '%Свердлов%'"
        )).fetchone()
        
        if not region:
            print("Region not found!")
            return
        
        region_id = str(region[0])
        
        # Clear existing districts for this region
        conn.execute(text(
            "DELETE FROM districts WHERE region_id = :rid"
        ), {"rid": region_id})
        conn.commit()
        print(f"\nCleared existing districts")
        
        # Match and insert
        matched = []
        unmatched_osm = []
        used_officials = set()
        
        for feat in features:
            official = match_osm_to_official(feat['name'], OFFICIAL_DISTRICTS)
            
            if official and official not in used_officials:
                matched.append((official, feat))
                used_officials.add(official)
            else:
                unmatched_osm.append(feat['name'])
        
        # Insert matched
        inserted = 0
        for name, feat in matched:
            geojson_str = json.dumps(feat['geometry'])
            try:
                conn.execute(text("""
                    INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                    VALUES (:id, :rid, :name,
                            ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                            ST_SimplifyPreserveTopology(
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                            NOW())
                """), {
                    'id': str(uuid4()),
                    'rid': region_id,
                    'name': name,
                    'geojson': geojson_str,
                })
                inserted += 1
                print(f"  + {name}")
            except Exception as e:
                print(f"  ! {name}: {str(e)[:60]}")
        
        conn.commit()
        
        # Report
        print(f"\n{'='*60}")
        print(f"Inserted: {inserted}")
        print(f"Unmatched official ({len(OFFICIAL_DISTRICTS) - len(used_officials)}):")
        for name in OFFICIAL_DISTRICTS:
            if name not in used_officials:
                print(f"  - {name}")
        
        if unmatched_osm:
            print(f"\nUnmatched OSM ({len(unmatched_osm)}):")
            for name in unmatched_osm:
                print(f"  - {name}")
        
        # Final count
        count = conn.execute(text(
            "SELECT COUNT(*) FROM districts WHERE region_id = :rid"
        ), {"rid": region_id}).scalar()
        print(f"\nFinal district count: {count}")


if __name__ == "__main__":
    main()
