import requests
import json
import pandas as pd
import logging
import time
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# List of API URLs for 2012–2024
api_urls = [
    f"https://banks.data.fdic.gov/api/sod?filters=STALPBR:HI%20AND%20YEAR:{year}&fields=NAMEFULL,NAMEBR,ZIPBR,DEPSUMBR,ADDRESBR&sort_by=NAMEBR&sort_order=ASC&limit=10000&offset=0&format=json"
    for year in range(2012, 2025)
]

# Function to clean text
def clean_text(text):
    if not isinstance(text, str):
        return "UNKNOWN"
    # Remove punctuation, normalize spaces
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text.strip())
    text = text.replace("STREET", "ST").replace("AVENUE", "AVE").replace("ROAD", "RD")
    return text.upper()

# Initialize data storage
all_data = []
index = 12  # Starting index for years (2012 + index - 12)
years = list(range(2012, 2025))

# Fetch data for each year
for url in api_urls:
    year = 2012 + index - 12
    offset = 0
    year_data = []
    
    logging.info(f"Fetching data for year {year}")
    retries = 3
    for attempt in range(retries):
        try:
            while True:
                # Update offset in URL
                url_with_offset = f"{url.split('&offset=')[0]}&offset={offset}"
                response = requests.get(url_with_offset, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                total_records = data.get("meta", {}).get("total", 0)
                logging.info(f"API response for {year} (offset {offset}): {total_records} total records expected")
                
                branches = data.get("data", [])
                if not branches:
                    logging.warning(f"No branches returned for year {year}, total expected: {total_records}")
                
                for branch in branches:
                    branch_info = branch.get("data", {})
                    if not all(key in branch_info for key in ["NAMEFULL", "NAMEBR", "ZIPBR", "DEPSUMBR", "ADDRESBR"]):
                        logging.warning(f"Incomplete branch data for year {year}: {branch_info}")
                        continue
                    branch_record = {
                        "NAMEFULL": branch_info["NAMEFULL"],
                        "NAMEBR": branch_info["NAMEBR"],
                        "ZIPBR": branch_info["ZIPBR"],
                        "DEPSUMBR": branch_info["DEPSUMBR"],
                        "ADDRESBR": branch_info["ADDRESBR"],
                        "YEAR": year
                    }
                    year_data.append(branch_record)
                    if branch_info["ZIPBR"] in ["96797", "96740"]:
                        logging.info(f"Found branch at {branch_info['ADDRESBR']} ({branch_info['ZIPBR']}, {branch_info['NAMEBR']}) for {year}: DEPSUMBR={branch_info['DEPSUMBR']}")
                
                logging.info(f"Retrieved {len(year_data)} of {total_records} records for year {year}")
                if len(year_data) >= total_records or not branches:
                    break
                
                offset += 10000
            break
        except requests.RequestException as e:
            logging.error(f"API request failed for year {year}, attempt {attempt + 1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue
    
    unique_branches = len(set(f"{b['ADDRESBR']}_{b['ZIPBR']}" for b in year_data))
    logging.info(f"Unique branches for {year}: {unique_branches}")
    all_data.extend(year_data)
    index += 1

# Check if any data was retrieved
if not all_data:
    logging.error("No data retrieved for any year. Check API key, filters, or data availability.")
    exit(1)

# Convert to DataFrame
df = pd.DataFrame(all_data)
logging.info(f"Total records in DataFrame: {len(df)}")

# Verify required columns
required_columns = ["NAMEFULL", "NAMEBR", "ZIPBR", "DEPSUMBR", "ADDRESBR", "YEAR"]
if not all(col in df.columns for col in required_columns):
    missing_cols = [col for col in required_columns if col not in df.columns]
    logging.error(f"Missing columns in DataFrame: {missing_cols}")
    exit(1)

# Clean text fields
df["NAMEFULL"] = df["NAMEFULL"].apply(clean_text)
df["NAMEBR"] = df["NAMEBR"].apply(clean_text)
df["ADDRESBR"] = df["ADDRESBR"].apply(clean_text)
df["ZIPBR"] = df["ZIPBR"].astype(str).str.zfill(5)

# Ensure DEPSUMBR is numeric
try:
    df["DEPSUMBR"] = pd.to_numeric(df["DEPSUMBR"], errors="coerce").fillna(0)
except Exception as e:
    logging.error(f"Error converting DEPSUMBR to numeric: {e}")
    exit(1)

# Create a composite key
df["BranchKey"] = df["ADDRESBR"] + "_" + df["ZIPBR"]

# Log unique branches
unique_branches = len(df["BranchKey"].unique())
logging.info(f"Total unique branches across all years: {unique_branches}")
if unique_branches < 250:
    logging.warning(f"Only {unique_branches} unique branches found; expected ~300. Consider using SOD datasets or internal Bank of Hawaii data.")

# Deduplicate by taking max DEPSUMBR
df = df.groupby(["BranchKey", "YEAR", "NAMEFULL", "NAMEBR", "ZIPBR", "ADDRESBR"])["DEPSUMBR"].max().reset_index()

# Validate zeros for specific ZIPs
for zip_code in ["96797", "96740"]:
    branch_data = df[df["ZIPBR"] == zip_code]
    for year in years:
        year_data = branch_data[branch_data["YEAR"] == year]
        if year_data.empty or year_data["DEPSUMBR"].iloc[0] == 0:
            logging.warning(f"Zero or missing deposit for branch at ZIP {zip_code} ({year_data['ADDRESBR'].iloc[0] if not year_data.empty else 'N/A'}) in {year}")

# Get all unique branches (include all from 2012 onward)
all_branches = df[["BranchKey", "NAMEFULL", "NAMEBR", "ZIPBR", "ADDRESBR"]].drop_duplicates()

# Determine last year each branch appears
last_year = df.groupby("BranchKey")["YEAR"].max().reset_index()
last_year_dict = dict(zip(last_year["BranchKey"], last_year["YEAR"]))

# Pivot deposits
pivot_df = df.pivot_table(
    index=["BranchKey", "NAMEFULL", "NAMEBR", "ZIPBR", "ADDRESBR"],
    columns="YEAR",
    values="DEPSUMBR",
    fill_value=0,
    aggfunc="max"
).reset_index()

# Rename columns
pivot_df.columns = [
    "BranchKey",
    "Parent Bank",
    "Branch Name",
    "Zip Code",
    "Address",
] + [f"Deposits, {year} (in thousands)" for year in years]

# Set deposits to 0 for years after last appearance
for _, row in pivot_df.iterrows():
    branch_key = row["BranchKey"]
    last_active_year = last_year_dict.get(branch_key, 2012)
    for year in years:
        if year > last_active_year:
            pivot_df.loc[pivot_df["BranchKey"] == branch_key, f"Deposits, {year} (in thousands)"] = 0

# Use earliest data for NAMEFULL, NAMEBR, ZIPBR
df_sorted = df.sort_values(by="YEAR")
earliest_data = df_sorted.groupby("BranchKey")[["NAMEFULL", "NAMEBR", "ZIPBR", "ADDRESBR"]].first().reset_index()

# Log merge inputs for debugging
logging.info(f"pivot_df shape before merge: {pivot_df.shape}, columns: {list(pivot_df.columns)}")
logging.info(f"earliest_data shape: {earliest_data.shape}, columns: {list(earliest_data.columns)}")
logging.info(f"Unique BranchKey in pivot_df: {len(pivot_df['BranchKey'].unique())}")
logging.info(f"Unique BranchKey in earliest_data: {len(earliest_data['BranchKey'].unique())}")

# Merge earliest data, preserving all columns
pivot_df = pivot_df.merge(
    earliest_data[["BranchKey", "NAMEFULL", "NAMEBR", "ZIPBR"]],
    on="BranchKey",
    how="left"
)

# Update columns with earliest values
pivot_df["Parent Bank"] = pivot_df["NAMEFULL"].combine_first(pivot_df["Parent Bank"])
pivot_df["Branch Name"] = pivot_df["NAMEBR"].combine_first(pivot_df["Branch Name"])
pivot_df["Zip Code"] = pivot_df["ZIPBR"].combine_first(pivot_df["Zip Code"])

# Drop unnecessary columns
pivot_df = pivot_df.drop(columns=["NAMEFULL", "NAMEBR", "ZIPBR", "Address"])

# Reorder columns
output_columns = ["Parent Bank", "Branch Name", "Zip Code"] + [f"Deposits, {year} (in thousands)" for year in years]
pivot_df = pivot_df[output_columns + ["BranchKey"]]  # Keep BranchKey for sorting

# Handle missing values
pivot_df["Parent Bank"] = pivot_df["Parent Bank"].fillna("Unknown")
pivot_df["Branch Name"] = pivot_df["Branch Name"].fillna("Unknown")
pivot_df["Zip Code"] = pivot_df["Zip Code"].fillna("Unknown")

# Remove duplicates by BranchKey
pivot_df["NonZeroCount"] = pivot_df[[f"Deposits, {year} (in thousands)" for year in years]].gt(0).sum(axis=1)
pivot_df = pivot_df.sort_values(by=["BranchKey", "NonZeroCount"], ascending=[True, False])
pivot_df = pivot_df.groupby("BranchKey").agg({
    "Parent Bank": "first",
    "Branch Name": "first",
    "Zip Code": "first",
    **{f"Deposits, {year} (in thousands)": "max" for year in years}
}).reset_index(drop=True)

# Reorder columns
pivot_df = pivot_df[output_columns]

# Final validation
unique_branches_final = len(pivot_df)
logging.info(f"Final unique branches: {unique_branches_final}")
if unique_branches_final < 250:
    logging.warning(f"Final branch count {unique_branches_final} is less than expected ~300. Consider using SOD datasets or internal Bank of Hawaii data.")

for _, row in pivot_df.iterrows():
    zip_code = row["Zip Code"]
    deposits = [row[f"Deposits, {year} (in thousands)"] for year in years]
    zero_years = [year for year, dep in zip(years, deposits) if dep == 0]
    if zero_years and zip_code in ["96797", "96740"]:
        logging.warning(f"Zero deposits for branch at ZIP {zip_code} ({row['Branch Name']}) in years: {zero_years}")

# Convert to JSON
output_data = pivot_df.to_dict(orient="records")

# Save to JSON
with open("hawaii_branches_blended_2012_2024.json", "w") as f:
    json.dump(output_data, f, indent=2)

# Save to CSV
pivot_df.to_csv("hawaii_branches_blended_2012_2024.csv", index=False)

logging.info(f"Processed {len(output_data)} branch records for Hawaii (2012–2024).")