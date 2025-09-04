import json
import pandas as pd

# 1. Load your raw data from JSON
with open('cagr_dep_data/hawaii_branches_blended_2012_2024.json', 'r') as f:
    data = json.load(f)

# 2. Convert into a pandas DataFrame
df = pd.DataFrame(data)

# 3. Figure out which columns are your “Deposits, YYYY (in thousands)”
deposit_cols = [col for col in df.columns if col.startswith('Deposits')]

# 4. Build an aggregation map:
#    - Sum every deposit column
#    - For Zip Code, just take the first value seen in each group
agg_map = {col: 'sum' for col in deposit_cols}
agg_map['Zip Code'] = 'first'

# 5. Group by Parent Bank + Branch Name, then apply those aggregations
grouped = (
    df
    .groupby(['Parent Bank', 'Branch Name'], as_index=False)
    .agg(agg_map)
)

# 6. (Optional) reorder your columns so Zip Code comes right after Branch Name
#    — this makes the JSON a bit more readable
cols_order = [
    'Parent Bank',
    'Branch Name',
    'Zip Code',
] + deposit_cols
grouped = grouped[cols_order]

# 7. Write the result out to a new JSON file
grouped.to_json(
    'summed_deposits_with_zip.json',
    orient='records',  # one object per row, wrapped in a list
    indent=2           # 2-space pretty-printing
)