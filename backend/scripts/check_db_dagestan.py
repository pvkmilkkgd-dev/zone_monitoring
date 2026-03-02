# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Дагестан' ORDER BY d.name
    """)).fetchall()
    print(f"DB districts: {len(rows)}")
    for r in rows:
        print(f"  {r[0]}")
