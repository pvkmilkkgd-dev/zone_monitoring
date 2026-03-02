"""Fix 241 districts with short names - get official names from OKTMO"""
import sys, requests, time
from bs4 import BeautifulSoup
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

def get_oktmo_names(region_name):
    """Get official district names from OKTMO for a region"""
    try:
        url = "https://www.okp-okpd.ru/oktmo.html"
        params = {'search': region_name}
        resp = requests.get(url, params=params, timeout=30)
        resp.encoding = 'windows-1251'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find region link
        region_link = None
        for a in soup.find_all('a'):
            text_content = a.get_text(strip=True)
            if region_name.lower() in text_content.lower():
                href = a.get('href', '')
                if 'oktmo' in href:
                    region_link = href
                    break
        
        if not region_link:
            return []
        
        if not region_link.startswith('http'):
            region_link = 'https://www.okp-okpd.ru/' + region_link
        
        resp2 = requests.get(region_link, timeout=30)
        resp2.encoding = 'windows-1251'
        soup2 = BeautifulSoup(resp2.text, 'html.parser')
        
        names = []
        for a in soup2.find_all('a'):
            text_content = a.get_text(strip=True)
            href = a.get('href', '')
            if 'oktmo' in href and text_content and len(text_content) > 3:
                # Skip the region name itself and codes
                if not any(c.isdigit() for c in text_content[:3]):
                    names.append(text_content)
        
        return names
    except Exception as ex:
        print(f"  Error fetching OKTMO for {region_name}: {ex}")
        return []


# Get all districts with short names grouped by region
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.id, d.name, r.name as region_name, r.id as region_id
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name NOT LIKE '%район%'
          AND d.name NOT LIKE '%округ%'
          AND d.name NOT LIKE '%город%'
          AND d.name NOT LIKE '%ЗАТО%'
          AND d.name NOT LIKE '%поселение%'
        ORDER BY r.name, d.name
    """)).fetchall()

# Group by region
from collections import defaultdict
by_region = defaultdict(list)
for r in rows:
    by_region[r[2]].append({'id': r[0], 'name': r[1], 'region_id': r[3]})

print(f"Found {len(rows)} districts with short names across {len(by_region)} regions\n")

fixed = 0
not_found = 0

for region_name, districts in sorted(by_region.items()):
    print(f"\n=== {region_name} ({len(districts)} to fix) ===")
    
    oktmo_names = get_oktmo_names(region_name)
    time.sleep(0.5)
    
    if not oktmo_names:
        print(f"  Could not fetch OKTMO names, skipping")
        not_found += len(districts)
        continue
    
    # Try to match each short name to an OKTMO name
    for d in districts:
        short = d['name'].lower().strip()
        
        best_match = None
        for oktmo in oktmo_names:
            oktmo_lower = oktmo.lower()
            # Check if the short name is contained in the OKTMO name
            if short in oktmo_lower:
                # Prefer names with 'городской округ' or 'муниципальный район'
                if best_match is None:
                    best_match = oktmo
                elif len(oktmo) > len(best_match):
                    best_match = oktmo
        
        if best_match and best_match != d['name']:
            print(f"  {d['name']} -> {best_match}")
            with e.begin() as conn:
                conn.execute(text("UPDATE districts SET name = :new_name WHERE id = :did"),
                           {'new_name': best_match, 'did': d['id']})
            fixed += 1
        else:
            print(f"  {d['name']} -> NO MATCH FOUND")
            not_found += 1

print(f"\n\nSummary: Fixed {fixed}, Not found {not_found}")
