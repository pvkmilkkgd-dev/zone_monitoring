"""Wrapper to run reload for all regions except Sverdlovsk."""
import sys
import os
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)

# Monkey-patch sys.argv to avoid PowerShell encoding issues
sys.argv = ['reload_all_districts_osm.py']

from scripts.reload_all_districts_osm import get_all_regions, process_region, get_engine
from sqlalchemy import text
import time

SKIP_REGIONS = {"Свердловская область"}  # Already done

regions = get_all_regions()
print(f"Total regions: {len(regions)}")

to_process = [(rid, rname) for rid, rname in regions if rname not in SKIP_REGIONS]
print(f"To process: {len(to_process)} (skipping {len(SKIP_REGIONS)})\n")

total_inserted = 0
failed = []

for i, (region_id, region_name) in enumerate(to_process):
    print(f"\n[{i+1}/{len(to_process)}] {region_name}")
    
    inserted, osm_count = process_region(region_id, region_name)
    
    if osm_count < 0:
        print(f"    FAILED")
        failed.append(region_name)
    elif osm_count == 0:
        print(f"    EMPTY")
        failed.append(region_name)
    else:
        print(f"    OK: {inserted}/{osm_count}")
        total_inserted += inserted
    
    time.sleep(2)

print(f"\n{'='*60}")
print(f"Total districts loaded: {total_inserted}")

if failed:
    print(f"\nFailed ({len(failed)}):")
    for name in failed:
        print(f"  - {name}")

# Final stats
engine = get_engine()
with engine.connect() as conn:
    stats = conn.execute(text("""
        SELECT r.name, COUNT(d.id) as cnt
        FROM regions r
        LEFT JOIN districts d ON d.region_id = r.id
        GROUP BY r.name
        ORDER BY cnt, r.name
    """)).fetchall()

print(f"\nAll regions:")
for name, cnt in stats:
    print(f"  {cnt:4d}  {name}")
