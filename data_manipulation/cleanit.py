import json
import pandas as pd

# 1) Load the nested JSON
with open("soi_cache_2021.json") as f:
    raw = json.load(f)

# 2) Flatten out all the per-ZIP “data” lists into one big list of dicts
records = []
for zip_key, payload in raw.items():
    for rec in payload.get("data", []):
        # (each rec already has "zipCode" & "year")
        records.append(rec)

# 3) Normalize into a DataFrame
df = pd.json_normalize(records)

# 4) Drop the two unwanted fields
df = df.drop(columns=["agiGroup", "agiGroupId"])

# 5) Replace nulls with 0 so sums aren’t NaN
df = df.fillna(0)

# 6) (Optional) Coerce all other columns to numeric
#    This guarantees summable dtypes.
numeric_cols = df.columns.difference(["zipCode", "year"])
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

# 7) Group by ZIP & year, summing every metric
agg = (
    df
    .groupby(["zipCode", "year"], as_index=False)
    .sum()
)

# 8) Inspect or save
print(agg.head())
agg.to_json("hi_tax_by_zip_year.json", orient="records", indent=2)
