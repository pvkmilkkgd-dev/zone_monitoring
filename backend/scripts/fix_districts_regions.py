"""Fix districts - relink to new regions and load missing geometry."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy import create_engine, text
from app.core.config import settings

EXCEL_PATH = r'C:\Users\Lucky\Downloads\123.xlsx'

# Mapping Excel region names to DB region names
REGION_NAME_MAP = {
    "Кемеровская область - Кузбасс": "Кемеровская область",
    "Республика Татарстан (Татарстан)": "Республика Татарстан",
    "Чувашская Республика - Чувашия": "Чувашская Республика",
    "Ханты-Мансийский автономный округ - Югра": "Ханты-Мансийский автономный округ — Югра",
    "Республика Северная Осетия — Алания": "Республика Северная Осетия - Алания",  # em-dash to hyphen
    "Республика Северная Осетия - Алания": "Республика Северная Осетия - Алания",
}

def fix_districts():
    """Relink districts to correct regions and check status."""
    engine = create_engine(settings.DATABASE_URL)
    
    # Load Excel data
    print("Загрузка данных из Excel...")
    df = pd.read_excel(EXCEL_PATH, sheet_name='GO_MR')
    print(f"  Загружено {len(df)} записей")
    
    # Get current regions
    print("\nПолучение списка регионов из БД...")
    with engine.connect() as conn:
        regions = conn.execute(text("SELECT id, name FROM regions")).fetchall()
        region_map = {r[1]: r[0] for r in regions}
        print(f"  Найдено {len(region_map)} регионов")
    
    # Clear and reload districts
    print("\nОчистка таблицы districts...")
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE districts CASCADE"))
        conn.commit()
    
    # Insert districts from Excel
    print("\nЗагрузка районов из Excel...")
    success = 0
    errors = []
    
    with engine.connect() as conn:
        for _, row in df.iterrows():
            region_name = row['Официальное название субъекта РФ']
            district_name = row['Официальное название ГО или МР']
            admin_center = row['Официальное название административного центра']
            
            # Map region name if needed
            region_name = REGION_NAME_MAP.get(region_name, region_name)
            
            # Find region
            region_id = region_map.get(region_name)
            
            if not region_id:
                errors.append(f"Регион не найден: {region_name}")
                continue
            
            try:
                conn.execute(text("""
                    INSERT INTO districts (id, region_id, name, created_at)
                    VALUES (gen_random_uuid(), :region_id, :name, NOW())
                """), {"region_id": region_id, "name": district_name})
                success += 1
            except Exception as e:
                errors.append(f"{district_name}: {e}")
        
        conn.commit()
    
    print(f"\nУспешно загружено: {success}")
    print(f"Ошибок: {len(errors)}")
    
    if errors[:10]:
        print("\nПервые ошибки:")
        for e in errors[:10]:
            print(f"  - {e}")
    
    # Check result
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ:")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN d.geom IS NOT NULL THEN 1 ELSE 0 END) as with_geom
            FROM districts d
            JOIN regions r ON d.region_id = r.id
        """)).fetchone()
        
        print(f"  Всего районов (с регионами): {result[0]}")
        print(f"  С геометрией: {result[1]}")
        print(f"  Без геометрии: {result[0] - result[1]}")


if __name__ == "__main__":
    fix_districts()
