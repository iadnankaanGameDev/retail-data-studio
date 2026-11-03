
from pathlib import Path
import sys
import pandas as pd
import json
from datetime import datetime
import argparse
from paths import (
    BASE_DIR,
    INCOMING_DIR,
    RAW_DIR,
    PROCESSED_DIR,
    QUARANTINE_DIR,
    resolve_project_path
)


parser = argparse.ArgumentParser(
    description="Validate incoming sales data"
)

parser.add_argument(
    "filename",
    help="CSV filename in data/incoming"
)

parser.add_argument(
    "--output-dir",
    default=str(PROCESSED_DIR),
    help="Directory for validated data and summaries"
)

parser.add_argument(
    "--quarantine-dir",
    default=str(QUARANTINE_DIR),
    help="Directory for rejected records"
)


parser.add_argument("--incoming-dir", default=str(INCOMING_DIR),
                    help="Directory containing the input CSV")
parser.add_argument("--reference-dir", default=str(RAW_DIR))
args = parser.parse_args()

filename = args.filename


incoming = pd.read_csv(resolve_project_path(args.incoming_dir) / filename)

required = ["Sale_ID", "Date", "Store_ID", "Product_ID", "Units"]

missing = [col for col in required if col not in incoming.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

# Convert values for validation without changing original data
ids = pd.to_numeric(incoming["Sale_ID"], errors="coerce")
dates = pd.to_datetime(
    incoming["Date"], format="%Y-%m-%d", errors="coerce"
)
units = pd.to_numeric(incoming["Units"], errors="coerce")

# Reference data
products = pd.read_csv(resolve_project_path(args.reference_dir) / "products.csv")
stores = pd.read_csv(resolve_project_path(args.reference_dir) / "stores.csv")

# Incoming foreign keys
product_ids = pd.to_numeric(
    incoming["Product_ID"], errors="coerce"
)
store_ids = pd.to_numeric(
    incoming["Store_ID"], errors="coerce"
)

invalid_product = (
    product_ids.isna()
    | ~product_ids.isin(products["Product_ID"])
)

invalid_store = (
    store_ids.isna()
    | ~store_ids.isin(stores["Store_ID"])
)


# Validation rules
invalid_id = ids.isna() | (ids <= 0) | (ids % 1 != 0)

checks = [
    (invalid_id, "Invalid Sale_ID"),
    (dates.isna(), "Invalid date"),
    (units.isna() | (units <= 0) | (units % 1 != 0),
     "Invalid units"),
    (ids.duplicated(keep=False) & ~invalid_id,
     "Duplicate Sale_ID in file"),
    (invalid_product, "Invalid Product_ID"),
    (invalid_store, "Invalid Store_ID"),
]

# Attach reasons to invalid records
reasons = pd.Series("", index=incoming.index, dtype="string")

for mask, message in checks:
    reasons.loc[mask] = reasons.loc[mask] + message + "; "

rejected_mask = reasons.ne("")

# Separate accepted and rejected records
accepted = incoming.loc[~rejected_mask].copy()
rejected = incoming.loc[rejected_mask].copy()

rejected["Error_Reason"] = (
    reasons.loc[rejected_mask].str.rstrip("; ")
)

# Normalize accepted records
accepted["Sale_ID"] = ids.loc[accepted.index].astype("int64")
accepted["Date"] = dates.loc[accepted.index].dt.strftime("%Y-%m-%d")
accepted["Units"] = units.loc[accepted.index].astype("int64")

accepted["Product_ID"] = (
    product_ids.loc[accepted.index].astype("int64")
)

accepted["Store_ID"] = (
    store_ids.loc[accepted.index].astype("int64")
)


# Create output directories
processed_dir = resolve_project_path(args.output_dir)
quarantine_dir = resolve_project_path(args.quarantine_dir)

processed_dir.mkdir(parents=True, exist_ok=True)
quarantine_dir.mkdir(parents=True, exist_ok=True)

# Save results
stem = Path(filename).stem

accepted.to_csv(
    processed_dir / f"{stem}_accepted.csv", index=False
)
rejected.to_csv(
    quarantine_dir / f"{stem}_rejected.csv", index=False
)

# Save structured validation results
validation_summary = {
    "source_file": filename,
    "processed_at": datetime.now().astimezone().isoformat(
        timespec="seconds"
    ),
    "total_records": int(len(incoming)),
    "validation_accepted": int(len(accepted)),
    "validation_rejected": int(len(rejected))
}

summary_path = (
    processed_dir / f"{stem}_validation_summary.json"
)

summary_path.write_text(
    json.dumps(
        validation_summary,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


print("\n=== PROCESSING RESULTS ===")
print(f"Total records: {len(incoming)}")
print(f"Accepted: {len(accepted)}")
print(f"Rejected: {len(rejected)}")
print("\nProcessing completed.")
