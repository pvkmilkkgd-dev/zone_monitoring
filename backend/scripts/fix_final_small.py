"""Fix remaining small issues."""
import sys, os
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

# Fix город-курорт entries in Ставрополь
print("=== Fix город-курорт entries ===")
with ENGINE.begin() as c:
    rows = c.execute(text(
        "SELECT id, name FROM districts WHERE name LIKE '%городской округ город-курорт%'"
    )).fetchall()
    for did, dname in rows:
        new_name = dname.replace('городской округ ', '')
        print(f"  {dname} -> {new_name}")
        c.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                 {'new': new_name, 'id': str(did)})

# Fix НАО - Заполярный и Нарьян-Мар
print("\n=== Fix НАО ===")
with ENGINE.begin() as c:
    rows = c.execute(text("""
        SELECT d.id, d.name FROM districts d 
        JOIN regions r ON d.region_id = r.id 
        WHERE r.name = 'Ненецкий автономный округ'
    """)).fetchall()
    for did, dname in rows:
        print(f"  Current: {dname}")
        if 'Заполярный' in dname and dname != 'Муниципальный район Заполярный район':
            c.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                     {'n': 'Муниципальный район Заполярный район', 'id': str(did)})
            print(f"    -> Муниципальный район Заполярный район")
        elif 'Нарьян' in dname and 'городской округ' not in dname:
            c.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                     {'n': 'городской округ Нарьян-Мар', 'id': str(did)})
            print(f"    -> городской округ Нарьян-Мар")

# Final check
print("\n=== Final check: districts without clear type designation ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, r.name as rn
        FROM districts d JOIN regions r ON d.region_id = r.id 
        WHERE d.name NOT LIKE '%%муниципальный%%'
        AND d.name NOT LIKE '%%городской%%'
        AND d.name NOT LIKE '%%город %%'
        AND d.name NOT LIKE '%%город-курорт%%'
        AND d.name NOT LIKE '%%ЗАТО%%'
        AND d.name NOT LIKE '%%рабочий%%'
        AND d.name NOT LIKE '%%округ%%'
        AND d.name NOT LIKE '%%район%%'
        AND d.name NOT LIKE '%%поселение%%'
        AND d.name NOT LIKE '%%поселок%%'
        AND d.name NOT LIKE '%%Бежтинский%%'
        AND d.name NOT LIKE '%%административный%%'
        AND d.name NOT LIKE '%%Муниципальный%%'
        ORDER BY r.name, d.name
    """)).fetchall()
    
    print(f"Remaining without type: {len(rows)}")
    for dname, rn in rows:
        print(f"  [{rn}] {dname}")

# Show total district count by region
print("\n=== Total districts per region ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT r.name, COUNT(d.id) as cnt
        FROM regions r LEFT JOIN districts d ON d.region_id = r.id
        GROUP BY r.name ORDER BY r.name
    """)).fetchall()
    total = 0
    for rname, cnt in rows:
        total += cnt
        print(f"  {rname}: {cnt}")
    print(f"\nTotal districts: {total}")

print("\nDone!")
