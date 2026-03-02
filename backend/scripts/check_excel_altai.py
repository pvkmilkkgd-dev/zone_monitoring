import pandas as pd

df = pd.read_excel(r'c:\Users\Lucky\Downloads\123.xlsx', sheet_name=None)
for sheet_name, sheet_df in df.items():
    cols = [c for c in sheet_df.columns if 'район' in str(c).lower() or 'го' in str(c).lower() or 'мр' in str(c).lower() or 'МР' in str(c) or 'ГО' in str(c)]
    if not cols:
        # Try looking for Алтайский край in all columns
        for col in sheet_df.columns:
            mask = sheet_df[col].astype(str).str.contains('Алтайский', na=False)
            if mask.any():
                print(f"Sheet: {sheet_name}, Column: {col}")
                print(sheet_df[mask].to_string())
                print()

# More thorough: check all sheets
print("=" * 60)
print("Looking for region column and district column...")
for sheet_name, sheet_df in df.items():
    print(f"\nSheet: {sheet_name}")
    print(f"Columns: {list(sheet_df.columns)}")
    # Find rows where 'Алтайский край' appears
    for col in sheet_df.columns:
        vals = sheet_df[col].astype(str)
        mask = vals.str.contains('Алтайский край', na=False)
        if mask.any():
            print(f"\n  Found 'Алтайский край' in column '{col}'")
            # Get all districts for this region
            idx = sheet_df.index[mask]
            # Look at surrounding rows to find district column
            for i in idx[:3]:
                print(f"  Row {i}: {dict(sheet_df.iloc[i])}")
            
            # Find district names - likely in next column or a specific column
            # Get all rows where this column = 'Алтайский край'
            altai_rows = sheet_df[mask]
            print(f"\n  Total rows with 'Алтайский край': {len(altai_rows)}")
            for _, row in altai_rows.iterrows():
                vals = [str(v) for v in row.values if str(v) != 'nan' and str(v) != 'Алтайский край']
                if vals:
                    print(f"    {vals}")
