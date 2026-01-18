import requests

region_id = "6e9be0a9-07e4-4150-a0e6-befb15b09618"
url = f"http://localhost:8000/api/maps/ru/region/{region_id}/boundary.geojson"

try:
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Type: {data.get('type')}")
        print(f"Features count: {len(data.get('features', []))}")
        if data.get('features'):
            feature = data['features'][0]
            print(f"Feature type: {feature.get('type')}")
            print(f"Geometry type: {feature.get('geometry', {}).get('type')}")
            print(f"Properties: {feature.get('properties')}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
