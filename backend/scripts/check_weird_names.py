"""Find districts with unusual names that might be settlement type descriptions
instead of proper municipal formation names."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.connect() as c:
    # 1. Names starting with "рабочий поселок" or "поселок"
    print("=== Подозрительные названия ===\n")
    
    queries = [
        ("'рабочий поселок%'", "рабочий поселок..."),
        ("'поселок %'", "поселок..."),
        ("'поселение %'", "поселение..."),
        ("'село %'", "село..."),
        ("'Город %'", "Город (с большой буквы)..."),
    ]
    
    for pattern, label in queries:
        rows = c.execute(text(f"""
            SELECT d.name, r.name FROM districts d 
            JOIN regions r ON d.region_id = r.id 
            WHERE d.name LIKE {pattern}
            ORDER BY r.name
        """)).fetchall()
        if rows:
            print(f"--- {label} ({len(rows)}) ---")
            for dname, rname in rows:
                print(f"  [{rname}] {dname}")
            print()
    
    # 2. Check names that look like they describe settlement type, not MO
    print("--- Прочие необычные ---")
    rows = c.execute(text("""
        SELECT d.name, r.name FROM districts d 
        JOIN regions r ON d.region_id = r.id 
        WHERE d.name NOT LIKE '%%муниципальный%%'
        AND d.name NOT LIKE '%%Муниципальный%%'
        AND d.name NOT LIKE '%%городской%%'
        AND d.name NOT LIKE '%%город %%'
        AND d.name NOT LIKE '%%город-курорт%%'
        AND d.name NOT LIKE '%%ЗАТО%%'
        AND d.name NOT LIKE '%%район%%'
        AND d.name NOT LIKE '%%округ%%'
        AND d.name NOT LIKE '%%административный%%'
        ORDER BY r.name, d.name
    """)).fetchall()
    if rows:
        print(f"  ({len(rows)} шт.)")
        for dname, rname in rows:
            print(f"  [{rname}] {dname}")
    else:
        print("  Нет")

    # 3. Show all names with "поселок" anywhere
    print("\n--- Все с 'поселок' в названии ---")
    rows = c.execute(text("""
        SELECT d.name, r.name FROM districts d 
        JOIN regions r ON d.region_id = r.id 
        WHERE d.name LIKE '%%поселок%%' OR d.name LIKE '%%посёлок%%'
        ORDER BY r.name
    """)).fetchall()
    for dname, rname in rows:
        print(f"  [{rname}] {dname}")
    
    # 4. Show all names with "рабочий" anywhere
    print("\n--- Все с 'рабочий' в названии ---")
    rows = c.execute(text("""
        SELECT d.name, r.name FROM districts d 
        JOIN regions r ON d.region_id = r.id 
        WHERE d.name LIKE '%%рабочий%%'
        ORDER BY r.name
    """)).fetchall()
    for dname, rname in rows:
        print(f"  [{rname}] {dname}")
