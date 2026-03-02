"""Check naming order: 'городской округ X' vs 'X городской округ'"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.name FROM districts d ORDER BY d.name
    """)).fetchall()

prefix_go = []  # "городской округ X"
suffix_go = []  # "X городской округ"
prefix_mo = []  # "муниципальный округ X"
suffix_mo = []  # "X муниципальный округ"
prefix_mr = []  # "муниципальный район X" (unlikely)
suffix_mr = []  # "X муниципальный район"

for (name,) in rows:
    nl = name.lower()
    if nl.startswith('городской округ '):
        prefix_go.append(name)
    elif 'городской округ' in nl and not nl.startswith('городской'):
        suffix_go.append(name)
    elif nl.startswith('муниципальный округ '):
        prefix_mo.append(name)
    elif 'муниципальный округ' in nl and not nl.startswith('муниципальный'):
        suffix_mo.append(name)
    elif nl.endswith('муниципальный район'):
        suffix_mr.append(name)
    elif nl.startswith('муниципальный район'):
        prefix_mr.append(name)

print(f"=== городской округ ===")
print(f"  Prefix 'городской округ X': {len(prefix_go)}")
for n in prefix_go[:5]:
    print(f"    {n}")
if len(prefix_go) > 5:
    print(f"    ... and {len(prefix_go)-5} more")

print(f"\n  Suffix 'X городской округ': {len(suffix_go)}")
for n in suffix_go[:5]:
    print(f"    {n}")
if len(suffix_go) > 5:
    print(f"    ... and {len(suffix_go)-5} more")

print(f"\n=== муниципальный округ ===")
print(f"  Prefix 'муниципальный округ X': {len(prefix_mo)}")
for n in prefix_mo[:5]:
    print(f"    {n}")
if len(prefix_mo) > 5:
    print(f"    ... and {len(prefix_mo)-5} more")

print(f"\n  Suffix 'X муниципальный округ': {len(suffix_mo)}")
for n in suffix_mo[:5]:
    print(f"    {n}")
if len(suffix_mo) > 5:
    print(f"    ... and {len(suffix_mo)-5} more")

print(f"\n=== муниципальный район ===")
print(f"  Suffix 'X муниципальный район': {len(suffix_mr)}")
print(f"  Prefix 'муниципальный район X': {len(prefix_mr)}")
