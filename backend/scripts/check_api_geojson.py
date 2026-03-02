"""Check API GeoJSON lon ranges for Chukotka."""
import sys, io, json, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = "http://localhost:8000/maps/ru/region/038f8b09-5f08-4816-8117-4acb6b9efa70/districts.geojson?v=3"
data = json.loads(urllib.request.urlopen(url).read())

for f in data["features"]:
    name = f["properties"]["name"]
    geom = f["geometry"]
    lons = []
    
    def collect(coords):
        if isinstance(coords[0], (int, float)):
            lons.append(coords[0])
        else:
            for c in coords:
                collect(c)
    
    collect(geom["coordinates"])
    print(f"{name}: {min(lons):.4f} .. {max(lons):.4f}")
