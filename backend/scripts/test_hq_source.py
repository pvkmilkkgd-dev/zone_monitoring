"""
Test different sources for high-quality OSM polygon geometry.
Compare point counts from:
1. Nominatim /lookup
2. polygons.openstreetmap.fr
3. Overpass full geometry download
"""
import sys, os, json, time, requests
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)

HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# Test with Лешуконский район (R1330714) - 205 pts currently, 28189 km2
TEST_RELATION = 1330714
TEST_NAME = "Лешуконский муниципальный округ"

def count_coords(geojson):
    """Count coordinate points in GeoJSON."""
    count = 0
    def process(coords):
        nonlocal count
        if isinstance(coords, list) and len(coords) > 0:
            if isinstance(coords[0], (int, float)):
                count += 1
            else:
                for item in coords:
                    process(item)
    process(geojson.get('coordinates', []))
    return count


def test_nominatim(osm_id):
    """Test Nominatim /lookup."""
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        'osm_ids': f'R{osm_id}',
        'format': 'json',
        'polygon_geojson': 1,
        'polygon_threshold': 0.0,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        if data:
            geojson = data[0].get('geojson')
            if geojson:
                pts = count_coords(geojson)
                return pts, geojson
    return 0, None


def test_osm_fr(osm_id):
    """Test polygons.openstreetmap.fr."""
    url = f"https://polygons.openstreetmap.fr/get_geojson.py?id={osm_id}&params=0"
    resp = requests.get(url, headers=HEADERS, timeout=60)
    if resp.status_code == 200:
        geojson = resp.json()
        if geojson:
            pts = count_coords(geojson)
            return pts, geojson
    return 0, None


def test_overpass_full(osm_id):
    """Test Overpass full geometry download."""
    query = f"""
[out:json][timeout:120];
relation({osm_id});
out geom;
"""
    resp = requests.post("https://overpass-api.de/api/interpreter",
                        data={'data': query}, timeout=150)
    if resp.status_code == 200:
        data = resp.json()
        elements = data.get('elements', [])
        if elements:
            el = elements[0]
            members = el.get('members', [])
            total_nodes = 0
            for m in members:
                geom = m.get('geometry', [])
                total_nodes += len(geom)
            return total_nodes, el
    return 0, None


print(f"Testing sources for R{TEST_RELATION} ({TEST_NAME})")
print("=" * 60)

# Test 1: Nominatim
print("\n1. Nominatim /lookup:")
pts, geojson = test_nominatim(TEST_RELATION)
print(f"   Points: {pts}")
if geojson:
    print(f"   Type: {geojson.get('type')}")
time.sleep(1.1)

# Test 2: OSM.fr polygons
print("\n2. polygons.openstreetmap.fr:")
pts2, geojson2 = test_osm_fr(TEST_RELATION)
print(f"   Points: {pts2}")
if geojson2:
    print(f"   Type: {geojson2.get('type')}")
time.sleep(1.1)

# Test 3: Overpass full
print("\n3. Overpass full geometry:")
pts3, data3 = test_overpass_full(TEST_RELATION)
print(f"   Total nodes: {pts3}")

# Compare
print(f"\n{'='*60}")
print("Comparison:")
print(f"  Nominatim:   {pts:>6d} points")
print(f"  OSM.fr:      {pts2:>6d} points")
print(f"  Overpass:    {pts3:>6d} nodes")

# If OSM.fr is better, test a couple more
if pts2 > pts:
    print(f"\nOSM.fr is {pts2/max(pts,1):.1f}x better!")
    
    # Test another district
    print("\nTesting Мезенский (R1330723, 292 pts)...")
    time.sleep(1.1)
    pts_n, _ = test_nominatim(1330723)
    time.sleep(1.1)
    pts_f, _ = test_osm_fr(1330723)
    print(f"  Nominatim: {pts_n}, OSM.fr: {pts_f}")
    
    print("\nTesting Вельский район (R1330727)...")
    time.sleep(1.1)
    pts_n2, _ = test_nominatim(1330727)
    time.sleep(1.1)
    pts_f2, _ = test_osm_fr(1330727)
    print(f"  Nominatim: {pts_n2}, OSM.fr: {pts_f2}")
