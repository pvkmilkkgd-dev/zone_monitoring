"""
Diagnose and fix Arkhangelsk Oblast geometry.
Issues:
1. Region polygon likely includes Nenets AO
2. Primorsky district is abnormally large (includes Arctic islands)
3. District coverage > 100% indicates overlaps
"""
import sys, os, json, time, re, requests
from uuid import uuid4

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}


def download_polygon_by_id(osm_id):
    """Download polygon from Nominatim by OSM relation ID."""
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {'osm_ids': f'R{osm_id}', 'format': 'json', 'polygon_geojson': 1}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                geojson = data[0].get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    return geojson, data[0].get('display_name', '')
    except Exception as e:
        print(f"  Error: {e}")
    return None, None


def main():
    print("=" * 60)
    print("Diagnosing Архангельская область")
    print("=" * 60)
    
    with ENGINE.connect() as c:
        region = c.execute(text(
            "SELECT id, name FROM regions WHERE name LIKE '%Архангел%'"
        )).fetchone()
        rid = str(region[0])
        
        # Check region vs Nenets
        nen = c.execute(text(
            "SELECT id FROM regions WHERE name LIKE '%Ненец%'"
        )).fetchone()
        nen_id = str(nen[0]) if nen else None
        
        # Check overlap between region and Nenets
        if nen_id:
            overlap = c.execute(text(
                "SELECT ST_Area(ST_Intersection(a.geom, b.geom)::geography)/1e6 "
                "FROM regions a, regions b "
                "WHERE a.id = :a AND b.id = :b"
            ), {"a": rid, "b": nen_id}).fetchone()
            print(f"Region overlap with Ненецкий АО: {overlap[0]:.0f} km2")
    
    # Step 1: Find the correct OSM relations for Arkhangelsk districts
    print("\nSearching Overpass for Arkhangelsk Oblast districts...")
    
    # Arkhangelsk Oblast OSM ID
    arkh_osm_id = 77677  # relation ID for Архангельская область
    area_id = 3600000000 + arkh_osm_id
    
    query = f"""
[out:json][timeout:120];
area({area_id})->.region;
relation["boundary"="administrative"]["admin_level"~"^(5|6)$"](area.region);
out tags;
"""
    print("  Querying Overpass...")
    try:
        resp = requests.post("https://overpass-api.de/api/interpreter",
                           data={'data': query}, timeout=150)
        if resp.status_code == 200:
            data = resp.json()
            elements = data.get('elements', [])
            print(f"  Found {len(elements)} elements")
            
            # Show all with their admin_level
            for el in sorted(elements, key=lambda x: x.get('tags', {}).get('name', '')):
                tags = el.get('tags', {})
                name = tags.get('name', '')
                al = tags.get('admin_level', '')
                osm_id = el['id']
                print(f"    R{osm_id} level={al} {name}")
        else:
            print(f"  HTTP {resp.status_code}")
            elements = []
    except Exception as e:
        print(f"  Error: {e}")
        elements = []
    
    # Step 2: Also try via name search
    if not elements:
        print("\n  Trying name-based search...")
        query = """
[out:json][timeout:120];
area["name"="Архангельская область"]["admin_level"="4"]->.region;
relation["boundary"="administrative"]["admin_level"~"^(5|6)$"](area.region);
out tags;
"""
        try:
            resp = requests.post("https://overpass-api.de/api/interpreter",
                               data={'data': query}, timeout=150)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get('elements', [])
                print(f"  Found {len(elements)} elements")
                for el in sorted(elements, key=lambda x: x.get('tags', {}).get('name', '')):
                    tags = el.get('tags', {})
                    print(f"    R{el['id']} level={tags.get('admin_level','')} {tags.get('name','')}")
        except Exception as e:
            print(f"  Error: {e}")
    
    if not elements:
        print("\nOverpass failed. Trying to fix individual districts manually.")
        # Check what's wrong with Primorsky
        print("\nChecking Приморский район...")
        # Search for the correct Primorsky rayon
        search_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': 'Приморский район, Архангельская область',
            'format': 'json',
            'limit': 5,
        }
        resp = requests.get(search_url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            for r in resp.json():
                print(f"  {r.get('osm_type','')}{r.get('osm_id','')} "
                      f"{r.get('class','')}/{r.get('type','')} "
                      f"{r.get('display_name','')[:80]}")
        return
    
    # Step 3: Filter out Nenets AO districts (they should be in their own region)
    # Nenets AO elements will have their boundary inside Nenets AO
    # For now, exclude anything that belongs to Nenets AO
    arkh_elements = []
    nen_names_lower = set()
    
    with ENGINE.connect() as c:
        if nen_id:
            nen_districts = c.execute(text(
                "SELECT name FROM districts WHERE region_id = :rid"
            ), {"rid": nen_id}).fetchall()
            nen_names_lower = {n[0].lower() for n in nen_districts}
    
    for el in elements:
        tags = el.get('tags', {})
        name = tags.get('name', '')
        # Skip if it's a Nenets AO district
        if name.lower() in nen_names_lower:
            print(f"  Skipping (Nenets): {name}")
            continue
        arkh_elements.append(el)
    
    print(f"\nFiltered to {len(arkh_elements)} Arkhangelsk districts")
    
    # Step 4: Reload districts
    print("\nReloading districts...")
    with ENGINE.connect() as c:
        c.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": rid})
        c.commit()
    
    loaded = 0
    for el in arkh_elements:
        tags = el.get('tags', {})
        name = tags.get('name', '')
        osm_id = el['id']
        
        geojson, display = download_polygon_by_id(osm_id)
        if geojson:
            try:
                with ENGINE.connect() as c:
                    c.execute(text("""
                        INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                        VALUES (:id, :rid, :name,
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                ST_SimplifyPreserveTopology(
                                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                                NOW())
                    """), {
                        'id': str(uuid4()), 'rid': rid,
                        'name': name, 'geojson': json.dumps(geojson),
                    })
                    c.commit()
                loaded += 1
                area_q = c.execute(text(
                    "SELECT ST_Area(geom::geography)/1e6 FROM districts WHERE name = :n AND region_id = :rid"
                ), {"n": name, "rid": rid}).fetchone()
                print(f"  OK {name} ({area_q[0]:.0f} km2)")
            except Exception as e:
                print(f"  Insert error {name}: {e}")
        else:
            print(f"  No polygon: {name} (R{osm_id})")
        time.sleep(1.1)
    
    print(f"\nLoaded: {loaded}/{len(arkh_elements)}")
    
    # Step 5: Rename via ОКТМО
    from bs4 import BeautifulSoup
    
    def normalize(name):
        n = name.strip().lower()
        for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
                  'район', 'округ', 'городской', 'город', 'зато', 'муниципальный']:
            n = n.replace(w, '')
        n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '')
        return n
    
    def transform_name(name):
        m = re.match(r'^город\s+(.+)$', name)
        if m:
            return f"городской округ {m.group(1)}"
        return name
    
    print("\nFetching ОКТМО names...")
    resp = requests.get("https://okp-okpd.ru/oktmo.aspx?kod=11", timeout=30)
    resp.encoding = 'windows-1251'
    soup = BeautifulSoup(resp.text, 'html.parser')
    oktmo_names = []
    for tr in soup.find_all('tr'):
        cells = tr.find_all('td')
        if len(cells) >= 2:
            code_text = cells[0].get_text(strip=True)
            name_text = cells[1].get_text(strip=True)
            if re.match(r'^\d{11}$', code_text):
                # Exclude Nenets AO entries
                if 'ненец' in name_text.lower():
                    continue
                oktmo_names.append(transform_name(name_text))
    
    print(f"ОКТМО names: {len(oktmo_names)}")
    for n in oktmo_names:
        print(f"  {n}")
    
    with ENGINE.connect() as c:
        rows = c.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid"
        ), {"rid": rid}).fetchall()
    
    db_by_norm = {normalize(n): (str(did), n) for did, n in rows}
    
    renames = 0
    for target in oktmo_names:
        tnorm = normalize(target)
        if tnorm in db_by_norm:
            did, dname = db_by_norm[tnorm]
            if dname != target:
                with ENGINE.connect() as c:
                    c.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                            {"n": target, "id": did})
                    c.commit()
                print(f"  Renamed: {dname} -> {target}")
                renames += 1
    
    print(f"Renamed: {renames}")
    
    # Final stats
    print(f"\n{'='*60}")
    with ENGINE.connect() as c:
        rows = c.execute(text(
            "SELECT name, ST_Area(geom::geography)/1e6 as area "
            "FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": rid}).fetchall()
        total = sum(r[1] for r in rows)
        rarea = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6 FROM regions WHERE id = :rid"
        ), {"rid": rid}).fetchone()[0]
    
    print(f"Districts: {len(rows)}")
    for name, area in rows:
        print(f"  {area:>10.0f} km2  {name}")
    print(f"\nTotal: {total:.0f} km2")
    print(f"Region: {rarea:.0f} km2")
    print(f"Coverage: {total/rarea*100:.1f}%")
    
    # Overall DB check
    with ENGINE.connect() as c:
        stats = c.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
    print(f"\nOverall DB: {stats[0]} districts, {stats[1]} with geometry")


if __name__ == "__main__":
    main()
