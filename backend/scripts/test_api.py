"""Test API endpoints."""
import sys
sys.path.insert(0, '.')

import requests

BASE_URL = "http://localhost:8000"

def test_regions():
    """Test /api/regions endpoint."""
    try:
        resp = requests.get(f"{BASE_URL}/api/regions", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Regions from /api/regions: {len(data)}")
            if data:
                print(f"  First: {data[0]['name']} (id: {data[0]['id'][:8]}...)")
        else:
            print(f"Error: HTTP {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")


def test_maps_geojson():
    """Test /maps/ru/regions.geojson endpoint."""
    try:
        resp = requests.get(f"{BASE_URL}/maps/ru/regions.geojson", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get('features', [])
            print(f"Features from /maps/ru/regions.geojson: {len(features)}")
            if features:
                props = features[0].get('properties', {})
                print(f"  First: {props.get('name')} (id: {str(props.get('id'))[:8]}...)")
        else:
            print(f"Error: HTTP {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_regions()
    test_maps_geojson()
