"""
Download and test GADM Level 2 data for Russia.
GADM often has higher detail boundaries than OSM for administrative areas.
"""
import sys, os, json, zipfile, io, requests
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)

HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# GADM 4.1 Russia Level 2 (districts)
GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_RUS_2.json.zip"
LOCAL_PATH = r"c:\Users\Lucky\Documents\zone_monitoring\backend\data\gadm41_RUS_2.json"

def count_coords(obj):
    count = 0
    def process(coords):
        nonlocal count
        if isinstance(coords, list) and len(coords) > 0:
            if isinstance(coords[0], (int, float)):
                count += 1
            else:
                for item in coords:
                    process(item)
    if 'coordinates' in obj:
        process(obj['coordinates'])
    return count

def main():
    os.makedirs(os.path.dirname(LOCAL_PATH), exist_ok=True)
    
    if not os.path.exists(LOCAL_PATH):
        print(f"Downloading GADM Russia Level 2...")
        print(f"URL: {GADM_URL}")
        resp = requests.get(GADM_URL, timeout=300, stream=True)
        total = int(resp.headers.get('content-length', 0))
        print(f"Size: {total/1024/1024:.1f} MB")
        
        data = io.BytesIO()
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=1024*1024):
            data.write(chunk)
            downloaded += len(chunk)
            print(f"  {downloaded/1024/1024:.1f} / {total/1024/1024:.1f} MB", end='\r')
        print()
        
        data.seek(0)
        with zipfile.ZipFile(data) as zf:
            names = zf.namelist()
            print(f"Files in zip: {names}")
            json_name = [n for n in names if n.endswith('.json')][0]
            with zf.open(json_name) as f:
                with open(LOCAL_PATH, 'wb') as out:
                    out.write(f.read())
        print(f"Extracted to {LOCAL_PATH}")
    else:
        print(f"Using cached: {LOCAL_PATH}")
    
    # Load and analyze
    print("\nLoading GADM data...")
    file_size = os.path.getsize(LOCAL_PATH)
    print(f"File size: {file_size/1024/1024:.1f} MB")
    
    with open(LOCAL_PATH, 'r', encoding='utf-8') as f:
        gadm = json.load(f)
    
    features = gadm.get('features', [])
    print(f"Total features: {len(features)}")
    
    # Find Arkhangelsk features
    arkh_features = []
    for feat in features:
        props = feat.get('properties', {})
        name1 = props.get('NAME_1', '')
        if 'Arkhangel' in name1 or 'Архангел' in name1:
            arkh_features.append(feat)
    
    print(f"\nArkhangelsk features: {len(arkh_features)}")
    for feat in arkh_features[:5]:
        props = feat.get('properties', {})
        pts = count_coords(feat.get('geometry', {}))
        print(f"  {props.get('NAME_2', ''):30s} {props.get('NL_NAME_2', ''):30s} {pts:>6d} pts")
    
    if len(arkh_features) > 5:
        print(f"  ... and {len(arkh_features)-5} more")
    
    # Show all with point counts
    print(f"\nAll Arkhangelsk GADM districts:")
    for feat in sorted(arkh_features, key=lambda f: f['properties'].get('NAME_2', '')):
        props = feat.get('properties', {})
        pts = count_coords(feat.get('geometry', {}))
        print(f"  {pts:>6d} pts  {props.get('NAME_2', ''):30s} {props.get('NL_NAME_2', '')}")
    
    # Compare with a specific district
    # Find Лешуконский
    for feat in features:
        props = feat.get('properties', {})
        name2 = (props.get('NAME_2', '') + props.get('NL_NAME_2', '')).lower()
        if 'лешукон' in name2 or 'leshuk' in name2:
            pts = count_coords(feat.get('geometry', {}))
            print(f"\nЛешуконский in GADM: {pts} pts")
            print(f"  vs OSM: 205 pts")
            break


if __name__ == "__main__":
    main()
