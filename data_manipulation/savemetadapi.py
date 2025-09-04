# ──────────────────────────────────────────
# 0) Imports + CONFIG (unchanged)
import json, time, requests, pandas as pd
from pathlib import Path
from tqdm import tqdm
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

API_BASE   = "https://global.metadapi.com/zipc/v1/zipcodes/{zipcode}/soi"
SUB_KEY    = "1563e01b99a344cdbba0885a4164534b"
# if you have other JSON (e.g. tax_by_zip.json), point to that here:
DEPOS_FILE = "cagr_dep_data/hi_deposits_2021_by_zip.json"

CACHE_FILE = "soi_cache_2021.json"
RATE_DELAY = 0.6
# ──────────────────────────────────────────

# 1) Load your deposit (or tax) JSON *only* to get the list of ZIP codes
with open(DEPOS_FILE) as f:
    raw = json.load(f)
# `raw` is a dict mapping ZIP → value; its keys are the ZIP strings you care about
zip_codes = list(raw.keys())

# 2) (Optional) if you still need those deposit values as y:
deposits = pd.Series(raw, name="deposits_$k")
# ensure string index
deposits.index = deposits.index.astype(str)

# 3) SOI fetch helper (unchanged)
def fetch_soi(zip_code: str) -> dict:
    cache = {}
    if Path(CACHE_FILE).exists():
        cache = json.loads(Path(CACHE_FILE).read_text())
    if zip_code in cache:
        return cache[zip_code]

    resp = requests.get(
        API_BASE.format(zipcode=zip_code),
        headers={
            "Accept": "application/json",
            "Ocp-Apim-Subscription-Key": SUB_KEY
        },
        timeout=15
    )
    resp.raise_for_status()
    soi = resp.json()
    cache[zip_code] = soi
    Path(CACHE_FILE).write_text(json.dumps(cache))
    time.sleep(RATE_DELAY)
    return soi

# 4) Pull SOI *only* for the ZIPs in your JSON
records = []
for zip_code in tqdm(zip_codes, desc="Pulling SOI"):
    soi = fetch_soi(zip_code)
    # if you want to keep the deposit value alongside:
    soi_flat = {**soi, "ZIP": zip_code, "deposits": raw[zip_code]}
    records.append(soi_flat)

df = pd.DataFrame.from_records(records).set_index("ZIP")

# 5) Proceed with your modeling
num_cols = df.select_dtypes(include="number").columns.drop("deposits")
X_all    = df[num_cols]
y        = df["deposits"]
