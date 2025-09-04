import json
from collections import defaultdict

# 1. Load the entire JSON array
# hi_tax_by_zip_year_pruned.json
with open('hi_tax_by_zip_year_pruned.json', 'r') as f:
    data = json.load(f)

# 2. Group records by year
by_year = defaultdict(list)
for rec in data:
    y = rec['year']
    by_year[y].append(rec)

# 3. Write out one file per year
for year, records in by_year.items():
    out_name = f"data_{year}.json"
    with open(out_name, 'w') as out:
        json.dump(records, out, indent=2)
    print(f"Wrote {len(records)} records → {out_name}")