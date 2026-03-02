"""Verify Altai Krai districts match official ОКТМО."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name FROM districts d 
        JOIN regions r ON d.region_id = r.id 
        WHERE r.name = 'Алтайский край'
        ORDER BY d.name
    """)).fetchall()

print(f"Алтайский край: {len(rows)} районов\n")

mo = [r[0] for r in rows if 'муниципальный округ' in r[0].lower() or 'Муниципальный округ' in r[0]]
mr = [r[0] for r in rows if 'муниципальный район' in r[0].lower()]
go = [r[0] for r in rows if 'город ' in r[0].lower() or 'городской округ' in r[0].lower()]
zato = [r[0] for r in rows if 'ЗАТО' in r[0]]
other = [r[0] for r in rows if r[0] not in mo + mr + go + zato]

print(f"Муниципальные округа ({len(mo)}):")
for n in sorted(mo):
    print(f"  {n}")

print(f"\nМуниципальные районы ({len(mr)}):")
for n in sorted(mr):
    print(f"  {n}")

print(f"\nГородские округа ({len(go)}):")
for n in sorted(go):
    print(f"  {n}")

print(f"\nЗАТО ({len(zato)}):")
for n in sorted(zato):
    print(f"  {n}")

if other:
    print(f"\nДругое ({len(other)}):")
    for n in sorted(other):
        print(f"  {n}")

print(f"\nИтого: {len(mo)} МО + {len(mr)} МР + {len(go)} ГО + {len(zato)} ЗАТО = {len(mo)+len(mr)+len(go)+len(zato)}")
