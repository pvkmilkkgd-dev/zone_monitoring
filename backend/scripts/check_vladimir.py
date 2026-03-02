import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.id, d.name, 
               ST_NPoints(d.geom) as pts,
               ROUND(ST_Area(d.geom::geography)/1e6) as area_km2
        FROM districts d 
        JOIN regions r ON d.region_id = r.id 
        WHERE r.name = 'Владимирская область'
        ORDER BY d.name
    """)).fetchall()
    
    print(f"Владимирская область: {len(rows)} районов\n")
    for did, dname, pts, area in rows:
        print(f"  {dname} (id={did}, pts={pts}, area={area} km2)")
    
    # Check ОКТМО for Vladimir
    print("\n\nОКТМО Владимирской области (code 17) на classinform.ru:")
    print("  17500000 - МО")
    print("  17600000 - МР") 
    print("  17700000 - ГО")
    print("\nПроверим дубликат:")
    dupes = c.execute(text("""
        SELECT d.id, d.name, ST_NPoints(d.geom) as pts,
               ROUND(ST_Area(d.geom::geography)/1e6) as area_km2,
               ST_AsText(ST_Centroid(d.geom)) as centroid
        FROM districts d 
        JOIN regions r ON d.region_id = r.id 
        WHERE r.name = 'Владимирская область' AND d.name LIKE '%Гусь%'
    """)).fetchall()
    for did, dname, pts, area, centroid in dupes:
        print(f"  {dname} id={did} pts={pts} area={area}km2 centroid={centroid}")
