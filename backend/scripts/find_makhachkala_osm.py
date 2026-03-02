# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.parse
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
    "q": "городской округ Махачкала",
    "format": "json",
    "polygon_geojson": "0"
})
req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
resp = urllib.request.urlopen(req, timeout=30)
data = json.loads(resp.read())
for d in data[:5]:
    print(f"osm_id={d.get('osm_id')}, type={d.get('osm_type')}, name={d.get('display_name')[:100]}")
if not data:
    print("No results")
