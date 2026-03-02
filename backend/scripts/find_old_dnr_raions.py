"""Find OLD (pre-2020 reform) raion boundaries in Donetsk Oblast using Overpass historical query."""
import requests
import json

overpass_url = "https://overpass-api.de/api/interpreter"

# Query with date before the 2020 Ukrainian reform (July 2020)
# Using date 2020-06-01 to get old admin_level=6 raions
query = """
[out:json][timeout:120][date:"2020-06-01T00:00:00Z"];
area["name"="Донецька область"]->.searchArea;
(
  relation["admin_level"="6"]["boundary"="administrative"](area.searchArea);
);
out tags;
"""

print("Querying Overpass for OLD (pre-2020) admin_level=6 in Donetsk Oblast...")
response = requests.post(overpass_url, data={"data": query})
data = response.json()

print(f"\nFound {len(data['elements'])} old raions:\n")

for element in sorted(data['elements'], key=lambda x: x.get('tags', {}).get('name:ru', x.get('tags', {}).get('name', ''))):
    tags = element.get('tags', {})
    name = tags.get('name', 'N/A')
    name_ru = tags.get('name:ru', 'N/A')
    admin_level = tags.get('admin_level', '?')
    print(f"R{element['id']:>10} | {name:45s} | ru: {name_ru}")
