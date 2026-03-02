"""Check Sverdlovsk in Excel."""
import pandas as pd

df = pd.read_excel(r'C:\Users\Lucky\Downloads\123.xlsx', sheet_name='GO_MR')

# Filter Sverdlovsk
sverdlovsk = df[df['Официальное название субъекта РФ'].str.contains('Свердлов', na=False)]

print(f"Sverdlovsk districts in Excel: {len(sverdlovsk)}")
print("\nDistricts:")
for _, row in sverdlovsk.iterrows():
    print(f"  {row['Официальное название ГО или МР']}")
