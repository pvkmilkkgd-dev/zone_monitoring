"""
Compare DB names vs Excel official names for Алтайский край.
Rename DB entries to match Excel, keep extras from OSM.
"""
import sys
import os
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

import pandas as pd
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

# Load Excel
df = pd.read_excel(r'c:\Users\Lucky\Downloads\123.xlsx', sheet_name='GO_MR')
altai_excel = df[df['Официальное название субъекта РФ'] == 'Алтайский край']
excel_names = sorted(altai_excel['Официальное название ГО или МР'].tolist())

# Load DB
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT d.id, d.name 
        FROM districts d
        JOIN regions r ON r.id = d.region_id
        WHERE r.name = 'Алтайский край'
        ORDER BY d.name
    """)).fetchall()

db_districts = [(str(r[0]), r[1]) for r in rows]
db_names = [r[1] for r in db_districts]

print(f"Excel: {len(excel_names)} districts")
print(f"DB:    {len(db_names)} districts")

# Normalize for comparison
def normalize(name):
    """Strip common suffixes for matching."""
    n = name.strip()
    for suffix in [' муниципальный район', ' район', ' муниципальный округ']:
        if n.endswith(suffix):
            n = n[:-len(suffix)]
    # Remove prefixes
    for prefix in ['муниципальный округ ', 'городской округ ']:
        if n.startswith(prefix):
            n = n[len(prefix):]
    return n.lower().replace('ё', 'е')

# Match Excel to DB
print("\n" + "=" * 70)
print("MATCHING Excel -> DB:")
print("=" * 70)

renames = []  # (db_id, old_name, new_name)
unmatched_excel = []

for excel_name in excel_names:
    excel_norm = normalize(excel_name)
    
    matched = False
    for db_id, db_name in db_districts:
        db_norm = normalize(db_name)
        if excel_norm == db_norm:
            if excel_name != db_name:
                renames.append((db_id, db_name, excel_name))
                print(f"  RENAME: '{db_name}' -> '{excel_name}'")
            else:
                print(f"  OK:     '{db_name}'")
            matched = True
            break
    
    if not matched:
        unmatched_excel.append(excel_name)
        print(f"  MISSING: '{excel_name}' (not in DB)")

# Find DB entries not in Excel
matched_db_ids = set(r[0] for r in renames)
matched_db_ids.update(
    db_id for db_id, db_name in db_districts
    for excel_name in excel_names
    if normalize(excel_name) == normalize(db_name)
)

extra_db = [(db_id, db_name) for db_id, db_name in db_districts if db_id not in matched_db_ids]

print(f"\n{'='*70}")
print(f"Extra in DB (not in Excel): {len(extra_db)}")
for _, name in extra_db:
    print(f"  {name}")

print(f"\nMissing from DB (in Excel): {len(unmatched_excel)}")
for name in unmatched_excel:
    print(f"  {name}")

print(f"\nRenames needed: {len(renames)}")

# Apply renames
if renames:
    print(f"\nApplying {len(renames)} renames...")
    with engine.connect() as conn:
        for db_id, old_name, new_name in renames:
            conn.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                        {"new": new_name, "id": db_id})
        conn.commit()
    print("Done!")

# Final list
print(f"\n{'='*70}")
print("FINAL DB districts for Алтайский край:")
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT d.name 
        FROM districts d
        JOIN regions r ON r.id = d.region_id
        WHERE r.name = 'Алтайский край'
        ORDER BY d.name
    """)).fetchall()

for i, (name,) in enumerate(rows, 1):
    # Mark if it's from Excel or extra
    is_excel = name in excel_names
    marker = "" if is_excel else " [OSM extra]"
    print(f"  {i:3d}. {name}{marker}")

print(f"\nTotal: {len(rows)} ({len(excel_names)} from Excel)")
