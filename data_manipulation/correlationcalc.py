# correlation_2021_by_zip.py
import json, time, requests, pandas as pd
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from tqdm import tqdm   # progress bar; pip install tqdm
# ──────────────────────────────────────────
# CONFIG
API_BASE   = "https://global.metadapi.com/zipc/v1/zipcodes/{zipcode}/soi"
SUB_KEY    = "29dfd90ed44c42e89ed79d11dbd0a65e"          #  ← put your key here or read from env
DEPOS_FILE = "hi_deposits_2021_by_zip.json"
CACHE_FILE = "soi_cache_2021.json"       # avoid re-hitting API
RATE_DELAY = 0.6                         # seconds between calls (respect quota)
# ──────────────────────────────────────────

# 1) target vector (y) ─────────────────────
deposits = pd.Series(json.loads(Path(DEPOS_FILE).read_text()),
                     name="deposits_$k")
deposits.index = deposits.index.astype(str)

# 2) SOI fetch helper with simple disk cache
def fetch_soi(zip_code: str) -> dict:
    # cache on disk so reruns are fast
    cache = {}
    if Path(CACHE_FILE).exists():
        cache = json.loads(Path(CACHE_FILE).read_text())
    if zip_code in cache:
        return cache[zip_code]

    url = API_BASE.format(zipcode=zip_code)
    headers = {
        "Accept": "application/json",
        "Ocp-Apim-Subscription-Key": SUB_KEY
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soi = resp.json()

    cache[zip_code] = soi
    Path(CACHE_FILE).write_text(json.dumps(cache))
    time.sleep(RATE_DELAY)
    return soi

# 3) Collect SOI data for all ZIPs in deposits
records = []
for zip_code in tqdm(deposits.index, desc="Pulling SOI"):
    soi = fetch_soi(zip_code)
    soi_flat = {**soi, "ZIP": zip_code, "deposits": deposits[zip_code]}
    records.append(soi_flat)

df = pd.DataFrame.from_records(records).set_index("ZIP")

# keep only numeric predictors
num_cols = df.select_dtypes(include="number").columns
X_all    = df[num_cols].drop(columns=["deposits"], errors="ignore")
y        = df["deposits"]

# 4) compute per-variable R²
results = {}
for col in X_all.columns:
    xi   = X_all[[col]].dropna()
    yi   = y.loc[xi.index]
    if len(xi) < 5:       # skip if too few data points
        continue
    model = LinearRegression().fit(xi, yi)
    r2    = r2_score(yi, model.predict(xi))
    results[col] = r2

r2_ranked = pd.Series(results).sort_values(ascending=False)
print("\nTop 15 SOI variables by R² with deposits (2021):")
print(r2_ranked.head(15).apply(lambda v: f"{v:.3f}"))

# 5) save full ranking
Path("soi_r2_rank_2021.json").write_text(r2_ranked.to_json(indent=2))
print("\n✓ Full ranking saved → soi_r2_rank_2021.json")