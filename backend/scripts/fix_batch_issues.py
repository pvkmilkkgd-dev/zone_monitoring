"""Fix batch of reported issues: names, wrong districts, etc."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

fixes = []

with e.begin() as c:
    # 1. "округ Муром" -> "городской округ Муром"
    r = c.execute(text("""
        UPDATE districts SET name = 'городской округ Муром'
        WHERE name = 'округ Муром'
    """))
    fixes.append(f"1. округ Муром -> городской округ Муром ({r.rowcount})")

    # 4. Дубенский район в Калужской — НЕ существует в Калужской обл. Удаляем.
    r = c.execute(text("""
        DELETE FROM districts
        WHERE name = 'Дубенский район'
        AND region_id = (SELECT id FROM regions WHERE name = 'Калужская область')
    """))
    fixes.append(f"4. Удалён Дубенский район из Калужской обл ({r.rowcount})")

    # 5. "Карачаевский район" -> "Карачаевский муниципальный район" в КЧР
    r = c.execute(text("""
        UPDATE districts SET name = 'Карачаевский муниципальный район'
        WHERE name = 'Карачаевский район'
        AND region_id = (SELECT id FROM regions WHERE name LIKE '%%Карачаево%%')
    """))
    fixes.append(f"5. Карачаевский район -> Карачаевский МР ({r.rowcount})")

    # 6. "Нерехтский район" -> "Нерехтский муниципальный район"
    r = c.execute(text("""
        UPDATE districts SET name = 'Нерехтский муниципальный район'
        WHERE name = 'Нерехтский район'
    """))
    fixes.append(f"6. Нерехтский район -> Нерехтский МР ({r.rowcount})")

    # 9. "Ковдорский район" -> "Ковдорский муниципальный район"
    r = c.execute(text("""
        UPDATE districts SET name = 'Ковдорский муниципальный район'
        WHERE name = 'Ковдорский район'
    """))
    fixes.append(f"9. Ковдорский район -> Ковдорский МР ({r.rowcount})")

    # 11. "Великий Новгород" -> "городской округ Великий Новгород"
    r = c.execute(text("""
        UPDATE districts SET name = 'городской округ Великий Новгород'
        WHERE name = 'Великий Новгород'
    """))
    fixes.append(f"11. Великий Новгород -> городской округ Великий Новгород ({r.rowcount})")

    # Also fix ALL remaining "X район" without "муниципальный"
    rows = c.execute(text("""
        SELECT id, name FROM districts
        WHERE name LIKE '%% район'
        AND name NOT LIKE '%%муниципальный%%'
        AND name NOT LIKE '%%Заполярный%%'
    """)).fetchall()
    
    for row in rows:
        old_name = row[1]
        # "X район" -> "X муниципальный район"
        new_name = old_name.replace(' район', ' муниципальный район')
        c.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                 {'new': new_name, 'id': row[0]})
    fixes.append(f"Extra: {len(rows)} 'X район' -> 'X муниципальный район'")

for f in fixes:
    print(f)

print("\nDone!")
