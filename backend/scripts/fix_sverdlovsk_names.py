"""Fix Sverdlovsk district names."""
import sys
import re
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)


def fix_name(name):
    """Fix district name."""
    # Remove "(горсовет)" and similar
    name = re.sub(r'\(горсовет\)', '', name)
    name = re.sub(r'\(город\)', '', name)
    
    # Split concatenated words
    # Pattern: word ending with "ий/ая/ое" + "район/район"
    name = re.sub(r'(\w+)(район)', r'\1 \2', name)
    name = re.sub(r'(\w+)(Тура|Пышма|Салда|Тагил|Лог)', r'\1 \2', name)
    
    # Clean up
    name = name.strip()
    name = ' '.join(name.split())  # normalize spaces
    
    # Remove "муниципальный район" duplicates
    if name.count('муниципальный район') > 1:
        name = name.replace('муниципальный район', '', 1).strip()
    
    # Ensure proper suffix
    if 'район' not in name.lower() and 'округ' not in name.lower():
        if 'NA' not in name:
            name = f"{name} городской округ"
    
    return name


with engine.connect() as conn:
    # Get Sverdlovsk districts
    districts = conn.execute(text("""
        SELECT d.id, d.name FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Свердлов%'
    """)).fetchall()
    
    print(f"Districts to fix: {len(districts)}")
    
    for d_id, old_name in districts:
        new_name = fix_name(old_name)
        
        if new_name != old_name:
            print(f"  {old_name[:40]} -> {new_name[:40]}")
            conn.execute(text(
                "UPDATE districts SET name = :new WHERE id = :id"
            ), {"new": new_name, "id": str(d_id)})
    
    conn.commit()
    
    # Delete NA
    conn.execute(text("""
        DELETE FROM districts d
        USING regions r
        WHERE d.region_id = r.id 
          AND r.name LIKE '%Свердлов%'
          AND d.name LIKE '%NA%'
    """))
    conn.commit()
    
    # Final count
    final = conn.execute(text("""
        SELECT COUNT(*) FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Свердлов%'
    """)).scalar()
    
    print(f"\nFinal count: {final}")
