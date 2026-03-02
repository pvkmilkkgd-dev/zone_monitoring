"""Manual fix for autonomous okrugs and remaining districts without types.
Based on actual ОКТМО data from classinform.ru (checked manually).
"""
import sys, os
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)


def get_region_id(name):
    with ENGINE.connect() as c:
        row = c.execute(text("SELECT id FROM regions WHERE name = :n"), {'n': name}).fetchone()
        return str(row[0]) if row else None


def rename_district(region_id, old_name_pattern, new_name):
    """Rename a district matching pattern in a region."""
    with ENGINE.begin() as c:
        result = c.execute(text(
            "UPDATE districts SET name = :new "
            "WHERE region_id = :rid AND name LIKE :pattern "
            "AND name != :new RETURNING name"
        ), {'new': new_name, 'rid': region_id, 'pattern': old_name_pattern})
        for row in result:
            print(f"  {row[0]} -> {new_name}")
            return True
    return False


# ====================================
# 1. ХМАО - fix unmatched МР districts
# ====================================
print("=== ХМАО: fix МР districts ===")
hmao_id = get_region_id('Ханты-Мансийский автономный округ - Югра')
if hmao_id:
    # ОКТМО official names for HMAO МР:
    hmao_mr = [
        ('Белоярский%район%', 'Белоярский муниципальный район'),
        ('Берёзовский%район%', 'Берёзовский муниципальный район'),
        ('%Березовский%район%', 'Берёзовский муниципальный район'),  # alt spelling
        ('Кондинский%район%', 'Кондинский муниципальный район'),
        ('Нефтеюганский%район%', 'Нефтеюганский муниципальный район'),
        ('Нижневартовский%район%', 'Нижневартовский муниципальный район'),
        ('Октябрьский%район%', 'Октябрьский муниципальный район'),
        ('Советский%район%', 'Советский муниципальный район'),
        ('Сургутский%район%', 'Сургутский муниципальный район'),
        ('Ханты-Мансийский%район%', 'Ханты-Мансийский муниципальный район'),
    ]
    for pattern, new_name in hmao_mr:
        rename_district(hmao_id, pattern, new_name)


# ====================================
# 2. ЯНАО - fix unmatched districts
# ====================================
print("\n=== ЯНАО: fix districts ===")
yanao_id = get_region_id('Ямало-Ненецкий автономный округ')
if yanao_id:
    # From ОКТМО: МО (муниципальные округа, though labeled as ГО on classinform page 71930000)
    yanao_mo = [
        ('%Красноселькупский%', 'Муниципальный округ Красноселькупский район'),
        ('%Надымский%', 'Муниципальный округ Надымский район'),
        ('%Приуральский%', 'Муниципальный округ Приуральский район'),
        ('%Пуровский%', 'Муниципальный округ Пуровский район'),
        ('%Тазовский%', 'Муниципальный округ Тазовский район'),
        ('%Шурышкарский%', 'Муниципальный округ Шурышкарский район'),
        ('%Ямальский%', 'Муниципальный округ Ямальский район'),
    ]
    for pattern, new_name in yanao_mo:
        rename_district(yanao_id, pattern, new_name)
    
    # ГО (город Лабытнанги) - from ОКТМО section 71950000
    rename_district(yanao_id, '%Лабытнанги%', 'город Лабытнанги')


# ====================================
# 3. НАО - fix Заполярный район
# ====================================
print("\n=== НАО: fix districts ===")
nao_id = get_region_id('Ненецкий автономный округ')
if nao_id:
    rename_district(nao_id, '%Заполярный%', 'Муниципальный район Заполярный район')
    rename_district(nao_id, '%Нарьян%Мар%', 'городской округ Нарьян-Мар')


# ====================================
# 4. Fix 3 remaining districts without types
# ====================================
print("\n=== Fix remaining typeless districts ===")

# Свирское (Иркутская область) - ОКТМО name is just "Свирское"
# Under ГО category (25700000), this is a городской округ
irk_id = get_region_id('Иркутская область')
if irk_id:
    rename_district(irk_id, 'Свирское', 'городской округ Свирское')

# поселок Палана (Камчатский край) - this is a special case
# ОКТМО: "поселок Палана" under ГО 30700000
# It's actually "городской округ поселок Палана" or just "поселок Палана"
# Let me keep it as-is since ОКТМО just says "поселок Палана" and that IS the official name
kamch_id = get_region_id('Камчатский край')
if kamch_id:
    # Check if it exists as "поселок Палана" already
    with ENGINE.connect() as c:
        row = c.execute(text(
            "SELECT name FROM districts WHERE region_id = :rid AND name LIKE '%Палана%'"
        ), {'rid': kamch_id}).fetchone()
        if row:
            print(f"  Камчатка: '{row[0]}' - keeping as-is (ОКТМО official)")

# Город Кедровый (Томская область) - ОКТМО: "Город Кедровый"
tom_id = get_region_id('Томская область')
if tom_id:
    # "Город Кедровый" is already pretty clear, but ОКТМО capitalizes "Город"
    # Official ОКТМО name: "город Кедровый" (lowercase г)
    rename_district(tom_id, '%Кедровый%', 'город Кедровый')


# ====================================
# 5. Fix "Борисоглебский" that was partially renamed
# ====================================
print("\n=== Fix other partially-renamed districts ===")

# Check for various issues
with ENGINE.connect() as c:
    # "Муниципальный район Заполярный район" is weird - let me check what ОКТМО says
    # For НАО, ОКТМО page 11811000 says: "Муниципальный район Заполярный район"
    # This IS the official ОКТМО name (weird but official)
    
    # Check Ставропольский край - "городской округ город-курорт Ессентуки"
    # ОКТМО 07700000 says: "город-курорт Ессентуки" under ГО
    # So the official name with type would be "городской округ город-курорт Ессентуки" 
    # Or just "город-курорт Ессентуки" as ОКТМО says
    # Since it already has a type-like designation ("город-курорт"), let's use ОКТМО as-is
    stav_id = get_region_id('Ставропольский край')
    if stav_id:
        result = c.execute(text(
            "SELECT name FROM districts WHERE region_id = :rid AND name LIKE '%Ессентуки%'"
        ), {'rid': stav_id}).fetchone()
        if result:
            print(f"  Ставрополь: '{result[0]}'")

# Fix "город-курорт" entries - they already have a type-like designation
# ОКТМО has them as: город-курорт Ессентуки, город-курорт Кисловодск, etc.
# but we composed to "городской округ город-курорт X"
# Let's revert to ОКТМО form
if stav_id:
    with ENGINE.begin() as c2:
        # Get all city-resort entries
        rows = c.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid AND name LIKE '%город-курорт%'"
        ), {'rid': stav_id}).fetchall()
        for did, dname in rows:
            # Remove "городской округ " prefix if present
            if dname.startswith('городской округ город-курорт'):
                new_name = dname.replace('городской округ ', '')
                print(f"  {dname} -> {new_name}")
                c2.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                          {'new': new_name, 'id': str(did)})


# ====================================
# 6. Summary
# ====================================
print("\n=== Final check: districts without clear type ===")
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, r.name as region_name 
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
        ORDER BY r.name, d.name
    """)).fetchall()
    
    print(f"Remaining: {len(rows)}")
    for dname, rname in rows:
        print(f"  [{rname}] {dname}")

print("\nDone!")
