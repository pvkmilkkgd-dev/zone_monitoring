"""
Test GADM as a source for higher-quality geometry.
GADM Level 2 = Russian districts.
"""
import sys, os, json, requests
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)

HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# Check GADM for Russia - download the GeoJSON for admin level 2
# GADM provides data at: https://gadm.org/download_country.html
# Direct GeoJSON: https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_RUS_2.json.zip

# But that's a huge file. Let's first check what we can get from GADM API
# Or check if there's a tile/WFS service

# Alternative: use OpenDataSoft which hosts GADM data
# Let's test with the Overpass "out body" to see actual way detail

print("Test 1: Check Overpass way detail for Лешуконский район (R1330714)")
query = """
[out:json][timeout:120];
relation(1330714);
out body;
>;
out skel;
"""
resp = requests.post("https://overpass-api.de/api/interpreter",
                    data={'data': query}, timeout=150)
if resp.status_code == 200:
    data = resp.json()
    elements = data.get('elements', [])
    nodes = [e for e in elements if e['type'] == 'node']
    ways = [e for e in elements if e['type'] == 'way']
    relations = [e for e in elements if e['type'] == 'relation']
    print(f"  Nodes: {len(nodes)}")
    print(f"  Ways: {len(ways)}")
    print(f"  Relations: {len(relations)}")
    
    # Count total nodes in all ways
    total_way_nodes = sum(len(w.get('nodes', [])) for w in ways)
    print(f"  Total node refs in ways: {total_way_nodes}")
    
    # Build the polygon manually from ways
    # First get relation members
    rel = [e for e in elements if e['type'] == 'relation'][0]
    outer_ways = [m for m in rel.get('members', []) if m.get('role') == 'outer']
    inner_ways = [m for m in rel.get('members', []) if m.get('role') == 'inner']
    print(f"  Outer ways: {len(outer_ways)}")
    print(f"  Inner ways: {len(inner_ways)}")

print("\n" + "="*60)
print("Test 2: Compare with Пинежский район (R1330722)")
query2 = """
[out:json][timeout:120];
relation(1330722);
out body;
>;
out skel;
"""
resp2 = requests.post("https://overpass-api.de/api/interpreter",
                     data={'data': query2}, timeout=150)
if resp2.status_code == 200:
    data2 = resp2.json()
    elements2 = data2.get('elements', [])
    nodes2 = [e for e in elements2 if e['type'] == 'node']
    ways2 = [e for e in elements2 if e['type'] == 'way']
    print(f"  Nodes: {len(nodes2)}")
    print(f"  Ways: {len(ways2)}")
    total_way_nodes2 = sum(len(w.get('nodes', [])) for w in ways2)
    print(f"  Total node refs in ways: {total_way_nodes2}")

print("\n" + "="*60)
print("Test 3: Check a well-known region with good detail")
print("Вельский район (R1330727)")
query3 = """
[out:json][timeout:120];
relation(1330727);
out body;
>;
out skel;
"""
resp3 = requests.post("https://overpass-api.de/api/interpreter",
                     data={'data': query3}, timeout=150)
if resp3.status_code == 200:
    data3 = resp3.json()
    elements3 = data3.get('elements', [])
    nodes3 = [e for e in elements3 if e['type'] == 'node']
    ways3 = [e for e in elements3 if e['type'] == 'way']
    print(f"  Nodes: {len(nodes3)}")
    print(f"  Ways: {len(ways3)}")
    total_way_nodes3 = sum(len(w.get('nodes', [])) for w in ways3)
    print(f"  Total node refs in ways: {total_way_nodes3}")

# Build actual GeoJSON from Overpass data to compare
print("\n" + "="*60)
print("Test 4: Overpass 'out geom' for Лешуконский")
query4 = """
[out:json][timeout:120];
relation(1330714);
out geom;
"""
resp4 = requests.post("https://overpass-api.de/api/interpreter",
                     data={'data': query4}, timeout=150)
if resp4.status_code == 200:
    data4 = resp4.json()
    el = data4['elements'][0]
    members = el.get('members', [])
    total = 0
    for m in members:
        geom = m.get('geometry', [])
        total += len(geom)
    print(f"  Total geometry nodes from 'out geom': {total}")
    print(f"  Members: {len(members)}")
