"""Find OSM admin boundaries for Zaporizhzhia Oblast - old raions (pre-2020)."""
import requests

overpass_url = "https://overpass-api.de/api/interpreter"

# Historical query: raions as of 2020-06-01 (before Ukrainian reform)
query = """
[out:json][timeout:90][date:"2020-06-01T00:00:00Z"];
area["name"="Запорізька область"]->.a;
(
  relation["admin_level"="6"]["boundary"="administrative"](area.a);
);
out tags;
"""
print("Old (pre-2020) raions in Zaporizhzhia Oblast:")
r = requests.post(overpass_url, data={"data": query}, timeout=120)
data = r.json()
for el in sorted(data.get("elements", []), key=lambda x: x.get("tags", {}).get("name:ru", "")):
    tags = el.get("tags", {})
    name_ru = tags.get("name:ru", tags.get("name", "?"))
    print(f"  R{el['id']}  {name_ru}")
