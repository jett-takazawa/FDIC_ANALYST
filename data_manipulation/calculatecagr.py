import json
import pandas as pd
from pathlib import Path

# ---- paths to your two files -------------------------------------------------
p2012 = Path("hi_deposits_2012_by_zip.json")
p2014 = Path("hi_deposits_2014_by_zip.json")

# ---- load as Series (ZIP index → deposit value) ------------------------------
s17 = pd.Series(json.loads(p2012.read_text()), name="2012").astype(float)
s20 = pd.Series(json.loads(p2014.read_text()), name="2014").astype(float)

# ensure ZIPs are strings
s17.index = s17.index.astype(str)
s20.index = s20.index.astype(str)

# ---- align on ZIPs present in 2014 -------------------------------------------
df = pd.concat([s17, s20], axis=1).loc[s20.index]

# (optional) if a ZIP has no 2012 record, drop it or treat 2012 as 0
df.dropna(subset=["2012"], inplace=True)          # keep only ZIPs with both years
# df["2012"].fillna(0, inplace=True)              # <—- alternative if you want NaN CAGR for new branches

# ---- CAGR over 2012 → 2014 (2-year growth) -----------------------------------
years = 2
df["CAGR"] = (df["2014"] / df["2012"]) ** (1 / years) - 1
df["CAGR"] = df["CAGR"].round(6)                  # e.g., 0.086451 → 8.65 %

# ---- save result -------------------------------------------------------------
out = Path("hi_cagr_2012_to_2014_by_zip.json")
out.write_text(df["CAGR"].to_json(orient="index", indent=2))
print(f"✓ CAGR file written → {out}\nFirst few lines:\n", df.head())
