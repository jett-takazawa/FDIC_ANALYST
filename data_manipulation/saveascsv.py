import requests, pandas as pd, json, pathlib

API = (
    "https://banks.data.fdic.gov/api/sod?"
    "filters=STALPBR:HI%20AND%20YEAR:2020"
    "&fields=NAMEFULL,NAMEBR,ZIPBR,DEPSUMBR,ADDRESBR"
    "&sort_by=NAMEBR&sort_order=ASC&limit=10000&offset=0&format=json"
)

# 1. Pull the API payload
resp = requests.get(API, timeout=30)
resp.raise_for_status()
payload = resp.json()

# 2. Flatten: grab the *inner* dict for each row
rows = [row["data"] for row in payload["data"]]

# 3. DataFrame and clean types
df = pd.DataFrame(rows)
df["DEPSUMBR"] = pd.to_numeric(df["DEPSUMBR"], errors="coerce").fillna(0)

# 4. Aggregate by ZIP
totals = (
    df.groupby("ZIPBR")["DEPSUMBR"]
      .sum()
      .astype(int)          # deposits in whole dollars
      .sort_index()
      .to_dict()
)

# 5. Save + quick sanity checks
path = pathlib.Path("hi_deposits_2020_by_zip.json")
path.write_text(json.dumps(totals, indent=2))

print("✓ Saved →", path)
print("Unique ZIPs in 2021 branch data:", len(totals))
print("Sample 5 rows:", dict(list(totals.items())[:5]))
