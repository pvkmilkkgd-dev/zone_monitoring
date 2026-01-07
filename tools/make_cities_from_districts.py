import json
from pathlib import Path

districts_path = Path("frontend/public/maps/66/districts.geojson")
cities_path = Path("frontend/public/maps/66/cities.geojson")

data = json.loads(districts_path.read_text(encoding="utf-8"))


def iter_coords(geom):
  t = geom["type"]
  if t == "Polygon":
    for ring in geom["coordinates"]:
      for lng, lat in ring:
        yield lng, lat
  elif t == "MultiPolygon":
    for poly in geom["coordinates"]:
      for ring in poly:
        for lng, lat in ring:
          yield lng, lat


features = []
for f in data["features"]:
  props = f.get("properties") or {}
  district_id = str(props.get("id") or props.get("osm_id") or props.get("name") or "unknown")
  name = str(props.get("name") or props.get("name:ru") or "Район")

  coords = list(iter_coords(f["geometry"]))
  if not coords:
    continue

  lngs = [c[0] for c in coords]
  lats = [c[1] for c in coords]
  lng = (min(lngs) + max(lngs)) / 2.0
  lat = (min(lats) + max(lats)) / 2.0

  features.append({
      "type": "Feature",
      "properties": {
          "name": f"Центр: {name}",
          "district_id": district_id,
          "is_center": True
      },
      "geometry": {"type": "Point", "coordinates": [lng, lat]}
  })

out = {"type": "FeatureCollection", "features": features}
cities_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

print("OK ->", cities_path)
