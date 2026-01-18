"""
Упрощение геометрии районов и заполнение geom_simplified
"""
from app.db.session import SessionLocal
from sqlalchemy import text

def simplify_geometries():
    db = SessionLocal()
    
    try:
        print("Упрощение геометрии районов...")
        print("Это может занять некоторое время...")
        print()
        
        # Получаем регион
        region_id = db.execute(
            text("SELECT id FROM regions WHERE name LIKE '%Свердлов%'")
        ).scalar()
        
        # Обновляем geom_simplified с упрощенной геометрией
        # tolerance 0.001 ≈ 100 метров
        query = text("""
            UPDATE districts
            SET geom_simplified = ST_Multi(
                ST_SimplifyPreserveTopology(
                    ST_MakeValid(geom),
                    0.001
                )
            )
            WHERE region_id = :region_id
        """)
        
        db.execute(query, {"region_id": region_id})
        db.commit()
        
        # Проверяем результат
        check_query = text("""
            SELECT 
                name,
                ST_NPoints(geom) as original_points,
                ST_NPoints(geom_simplified) as simplified_points
            FROM districts
            WHERE region_id = :region_id
            ORDER BY name
            LIMIT 10
        """)
        
        print("Rezultat uproshheniya (pervye 10):")
        print()
        results = db.execute(check_query, {"region_id": region_id}).fetchall()
        for r in results:
            reduction = 100 * (1 - r.simplified_points / r.original_points)
            print(f"{r.name}:")
            print(f"  Original: {r.original_points} tochek")
            print(f"  Simplified: {r.simplified_points} tochek (-{reduction:.1f}%)")
        
        print()
        print("[OK] Geometriya uproshena!")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    simplify_geometries()
