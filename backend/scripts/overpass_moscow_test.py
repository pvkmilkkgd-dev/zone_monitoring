import requests, json
q = """[out:json][timeout:60];
area(2555133)->.moscow;
relation(area.moscow)["boundary"="administrative"]["admin_level"~"6|7|8"];
out ids;
"""
r = requests.post("https://overpass-api.de/api/interpreter", data={"data": q}, timeout=90)
d = r.json()
els = d.get("elements", [])
print("Relations admin_level=8:", len(els))
for e in els[:10]:
    t = e.get("tags") or {}
    print(" ", e.get("id"), t.get("name:ru") or t.get("name"))
