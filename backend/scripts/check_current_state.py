# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 1), ST_NumGeometries(d.geom)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Дагестан' AND d.geom IS NOT NULL
        ORDER BY d.name
    """)).fetchall()
    for r in rows:
        marker = " ***" if r[0] in ('городской округ г. Махачкала', 'Бабаюртовский муниципальный район', 'Тарумовский муниципальный район') else ""
        print(f"  {r[0]}: {r[1]} km2, {r[2]} parts{marker}")
