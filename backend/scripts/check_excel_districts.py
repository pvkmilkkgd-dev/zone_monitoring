"""Check Excel file structure for districts."""
import pandas as pd

# Read Excel file with all sheets
excel_path = r'C:\Users\Lucky\Downloads\123.xlsx'
df_dict = pd.read_excel(excel_path, sheet_name=None)

print("Листы в файле:", list(df_dict.keys()))

for sheet_name, sheet_df in df_dict.items():
    print(f"\n{'=' * 60}")
    print(f"=== {sheet_name} ===")
    print(f"Строк: {len(sheet_df)}, Колонок: {len(sheet_df.columns)}")
    print(f"Колонки: {list(sheet_df.columns)}")
    print(f"\nПервые 5 строк:")
    print(sheet_df.head(5).to_string())
    print(f"\nПоследние 3 строки:")
    print(sheet_df.tail(3).to_string())
