
from pathlib import Path
import sqlite3
import pandas as pd
import argparse

from paths import (
    RAW_DIR,
    PROCESSED_DIR,
    DEFAULT_DB_PATH,
    resolve_project_path
)

# Command-line arguments
parser = argparse.ArgumentParser(
    description="Generate sales analytics reports"
)

parser.add_argument(
    "--db-path",
    default=str(DEFAULT_DB_PATH),
    help="Source SQLite database"
)

parser.add_argument(
    "--output-dir",
    default=str(PROCESSED_DIR),
    help="Directory for generated reports"
)

parser.add_argument("--reference-dir", default=str(RAW_DIR))
args = parser.parse_args()

DB_PATH = resolve_project_path(args.db_path)
OUTPUT_DIR = resolve_project_path(args.output_dir)

# Verify database before connecting
if not DB_PATH.is_file():
    parser.error(f"Database not found: {DB_PATH}")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# 1. Read sales from our database
with sqlite3.connect(DB_PATH) as conn:
    sales = pd.read_sql_query("SELECT * FROM sales", conn)

products = pd.read_csv(resolve_project_path(args.reference_dir) / "products.csv")
stores = pd.read_csv(resolve_project_path(args.reference_dir) / "stores.csv")

# 2. Convert currency strings to numeric values
for col in ["Product_Price", "Product_Cost"]:
    values = (
        products[col]
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    products[col] = pd.to_numeric(values, errors="coerce")

    if products[col].isna().any() or (products[col] < 0).any():
        raise ValueError(f"Invalid values in {col}")

# 3. Match sales with product details
sales = sales.merge(
    products,
    on="Product_ID",
    how="left",
    validate="many_to_one",
    indicator="product_match"
)

if (sales["product_match"] == "left_only").any():
    raise ValueError("Some products could not be matched")

sales = sales.drop(columns="product_match")

# 4. Match sales with store details
sales = sales.merge(
    stores,
    on="Store_ID",
    how="left",
    validate="many_to_one",
    indicator="store_match"
)

if (sales["store_match"] == "left_only").any():
    raise ValueError("Some stores could not be matched")

sales = sales.drop(columns="store_match")

# 5. Calculate sales metrics
sales["Estimated_Revenue"] = (
    sales["Units"] * sales["Product_Price"]
).round(2)

# 6. Daily sales summary by store
daily_summary = (
    sales.groupby(
        ["Date", "Store_ID", "Store_Name"],
        as_index=False
    )
    .agg(
        Transactions=("Sale_ID", "count"),
        Units_Sold=("Units", "sum"),
        Estimated_Revenue=("Estimated_Revenue", "sum")
    )
)

daily_summary["Estimated_Revenue"] = (
    daily_summary["Estimated_Revenue"].round(2)
)

# 7. Sales summary by product category
category_summary = (
    sales.groupby("Product_Category", as_index=False)
    .agg(
        Transactions=("Sale_ID", "count"),
        Units_Sold=("Units", "sum"),
        Estimated_Revenue=("Estimated_Revenue", "sum")
    )
)

category_summary["Estimated_Revenue"] = (
    category_summary["Estimated_Revenue"].round(2)
)


# Verify consistency between source data and reports
expected_transactions = len(sales)
expected_units = int(sales["Units"].sum())

checks = {
    "Daily transactions": (
        int(daily_summary["Transactions"].sum()),
        expected_transactions
    ),
    "Category transactions": (
        int(category_summary["Transactions"].sum()),
        expected_transactions
    ),
    "Daily units sold": (
        int(daily_summary["Units_Sold"].sum()),
        expected_units
    ),
    "Category units sold": (
        int(category_summary["Units_Sold"].sum()),
        expected_units
    )
}

for name, (actual, expected) in checks.items():
    if actual != expected:
        raise ValueError(
            f"Reconciliation failed: {name}. "
            f"Expected {expected}, got {actual}."
        )


# Verify estimated revenue totals
expected_revenue = round(
    float(sales["Estimated_Revenue"].sum()), 2
)

daily_revenue = round(
    float(daily_summary["Estimated_Revenue"].sum()), 2
)

category_revenue = round(
    float(category_summary["Estimated_Revenue"].sum()), 2
)

if daily_revenue != expected_revenue:
    raise ValueError(
        "Daily revenue reconciliation failed"
    )

if category_revenue != expected_revenue:
    raise ValueError(
        "Category revenue reconciliation failed"
    )

print(f"Source estimated revenue: ${expected_revenue:,.2f}")
print(f"Daily summary revenue:   ${daily_revenue:,.2f}")
print(f"Category summary revenue:${category_revenue:,.2f}")
    

# Independent store-level check using SQLite
with sqlite3.connect(DB_PATH) as conn:
    expected_stores = pd.read_sql_query(
        """
        SELECT
            Store_ID,
            COUNT(*) AS Transactions,
            SUM(Units) AS Units_Sold
        FROM sales
        GROUP BY Store_ID
        ORDER BY Store_ID
        """,
        conn
    )

# Store totals calculated from the daily report
actual_stores = (
    daily_summary
    .groupby("Store_ID", as_index=False)
    .agg(
        Transactions=("Transactions", "sum"),
        Units_Sold=("Units_Sold", "sum")
    )
    .sort_values("Store_ID")
    .reset_index(drop=True)
)

# Compare all stores, not just grand totals
pd.testing.assert_frame_equal(
    expected_stores.reset_index(drop=True),
    actual_stores,
    check_dtype=False
)

print(
    f"Store-level reconciliation: PASSED "
    f"({len(expected_stores)} stores)"
)


# Independent category-level reconciliation
with sqlite3.connect(DB_PATH) as conn:
    product_totals = pd.read_sql_query(
        """
        SELECT
            Product_ID,
            COUNT(*) AS Transactions,
            SUM(Units) AS Units_Sold
        FROM sales
        GROUP BY Product_ID
        """,
        conn
    )

# Map each product to its category
expected_categories = product_totals.merge(
    products[["Product_ID", "Product_Category"]],
    on="Product_ID",
    how="left",
    validate="one_to_one"
)

if expected_categories["Product_Category"].isna().any():
    raise ValueError("Unmatched product categories found")

# Calculate expected category totals
expected_categories = (
    expected_categories
    .groupby("Product_Category", as_index=False)
    .agg(
        Transactions=("Transactions", "sum"),
        Units_Sold=("Units_Sold", "sum")
    )
    .sort_values("Product_Category")
    .reset_index(drop=True)
)

# Get category totals from our generated report
actual_categories = (
    category_summary[
        ["Product_Category", "Transactions", "Units_Sold"]
    ]
    .sort_values("Product_Category")
    .reset_index(drop=True)
)

pd.testing.assert_frame_equal(
    expected_categories,
    actual_categories,
    check_dtype=False
)

print(
    f"Category-level reconciliation: PASSED "
    f"({len(actual_categories)} categories)"
)


print("\nReport reconciliation: PASSED")


# 8. Export updated reports
daily_summary.to_csv(
    OUTPUT_DIR / "store_daily_summary.csv", index=False
)

category_summary.to_csv(
    OUTPUT_DIR / "category_summary.csv", index=False
)

print("\n=== REPORT GENERATION ===")
print(f"Sales processed: {len(sales):,}")
print(f"Daily summary rows: {len(daily_summary):,}")
print(f"Categories: {len(category_summary)}")
print("\nReports generated successfully.")
