"""Find correct OSM ID for Kherson Oblast."""
import requests
import time

# Search on Nominatim
url = 'https://nominatim.openstreetmap.org/search'
params = {
    'q': 'Kherson Oblast Ukraine',
    'format': 'json',
    'limit': 10,
}
headers = {'User-Agent': 'ZoneMonitoring/1.0'}

print("Searching for Kherson Oblast...")
resp = requests.get(url, params=params, headers=headers, timeout=30)
data = resp.json()

print(f"\nFound {len(data)} results:")
for item in data:
    osm_type = item.get('osm_type', '?')
    osm_id = item.get('osm_id', '?')
    name = item.get('display_name', '')[:80]
    print(f"  {osm_type[0].upper()}{osm_id}: {name}...")

# Also try direct lookup for various IDs
print("\n\nTrying direct lookups...")
test_ids = [72160, 71966, 1709607, 72155, 71965, 71967, 72164]

for osm_id in test_ids:
    url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{osm_id}&format=json"
    resp = requests.get(url, headers=headers, timeout=30)
    data = resp.json()
    
    if data:
        name = data[0].get('display_name', '')[:60]
        print(f"  R{osm_id}: {name}...")
    else:
        print(f"  R{osm_id}: Not found")
    
    time.sleep(1)
