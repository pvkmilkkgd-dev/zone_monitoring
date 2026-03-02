"""Fix geometry for problematic regions."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from download_region_geometry import fix_region, download_region, list_regions

PROBLEM_REGIONS = [
    "Донецкая Народная Республика",
    "Луганская Народная Республика", 
    "Запорожская область",
    "Херсонская область",
    "Республика Крым",
    "город Севастополь",
]

def main():
    print("=" * 60)
    print("ИСПРАВЛЕНИЕ ГЕОМЕТРИИ ПРОБЛЕМНЫХ РЕГИОНОВ")
    print("=" * 60)
    
    for region in PROBLEM_REGIONS:
        print(f"\n>>> {region}")
        
        # Пробуем Nominatim
        print("  Пробуем Nominatim...")
        if download_region(region, "nominatim"):
            print(f"  OK: {region}")
        else:
            # Пробуем Overpass
            print("  Пробуем Overpass...")
            time.sleep(2)
            if download_region(region, "overpass"):
                print(f"  OK (Overpass): {region}")
            else:
                print(f"  FAILED: {region}")
        
        time.sleep(2)  # Пауза между регионами
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТ:")
    list_regions()

if __name__ == "__main__":
    main()
