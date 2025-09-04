import pandas as pd

# 1) Load your aggregated JSON
json_path = "hi_tax_by_zip_year.json"
df = pd.read_json(json_path, orient="records")

# 2) Identify zero-only numeric columns
numeric = df.select_dtypes(include="number")
zero_only = numeric.columns[(numeric == 0).all()]

# 3) Drop those columns (plus any you already want gone)
to_drop = list(zero_only)  # e.g. ['returnsFarms', 'unemploymentCompensationAmount', ...]
df_clean = df.drop(columns=to_drop)

# 4) (Optional) verify
print("Dropped zero-only fields:", to_drop)
print("Remaining columns:", df_clean.columns.tolist())

# 5) Save the truly “live” fields back out
df_clean.to_json("hi_tax_by_zip_year_pruned.json", orient="records", indent=2)
