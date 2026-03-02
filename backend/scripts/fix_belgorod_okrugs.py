"""
Белгородская область: заменить старые составные названия на актуальные ОКТМО.
- Муниципальный район Алексеевский район и город Алексеевка → Алексеевский муниципальный округ
- Муниципальный район Город Валуйки и Валуйский район → Валуйский муниципальный округ
- Муниципальный район Шебекинский район и город Шебекино → Шебекинский муниципальный округ
"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

replacements = [
    ("Муниципальный район Алексеевский район и город Алексеевка", "Алексеевский муниципальный округ"),
    ("Муниципальный район Город Валуйки и Валуйский район", "Валуйский муниципальный округ"),
    ("Муниципальный район Шебекинский район и город Шебекино", "Шебекинский муниципальный округ"),
]

with ENGINE.begin() as c:
    for old_name, new_name in replacements:
        r = c.execute(text("""
            UPDATE districts d SET name = :new
            FROM regions r WHERE d.region_id = r.id AND r.name = 'Белгородская область' AND d.name = :old
        """), {"old": old_name, "new": new_name})
        print(f"  {old_name[:50]}... → {new_name}")

with ENGINE.connect() as c:
    for part in ["Алексеев", "Валуй", "Шебекин"]:
        row = c.execute(text("""
            SELECT d.name FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name = 'Белгородская область' AND d.name LIKE :p
        """), {"p": f"%{part}%"}).fetchall()
        print(f"  В базе ({part}): {[r[0] for r in row]}")
