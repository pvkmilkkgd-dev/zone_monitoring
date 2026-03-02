"""Find all admin boundaries within Donetsk Oblast from OSM via Overpass API."""
import requests
import json

overpass_url = "https://overpass-api.de/api/interpreter"

# Query for admin_level 6 and 7 within Donetsk Oblast
query = """
[out:json][timeout:120];
area["name"="Донецька область"]->.searchArea;
(
  relation["admin_level"="6"](area.searchArea);
  relation["admin_level"="7"](area.searchArea);
);
out tags;
"""

print("Querying Overpass API for admin boundaries in Donetsk Oblast...")
response = requests.post(overpass_url, data={"data": query})
data = response.json()

print(f"\nFound {len(data['elements'])} relations:\n")

for element in sorted(data['elements'], key=lambda x: (x.get('tags', {}).get('admin_level', ''), x.get('tags', {}).get('name', ''))):
    tags = element.get('tags', {})
    name = tags.get('name', 'N/A')
    name_ru = tags.get('name:ru', 'N/A')
    admin_level = tags.get('admin_level', '?')
    boundary = tags.get('boundary', '')
    print(f"R{element['id']:>10} | lvl={admin_level} | {name:45s} | ru: {name_ru}")
