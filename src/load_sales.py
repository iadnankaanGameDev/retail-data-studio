
from pathlib import Path
import sqlite3
import pandas as pd
import sys
import json
from datetime import datetime
import argparse
from paths import (
    DEFAULT_DB_PATH,
    PROCESSED_DIR,
    QUARANTINE_DIR,
    resolve_project_path
)



# Command-line arguments
parser = argparse.ArgumentParser(
    description="Load validated sales into SQLite"
)

parser.add_argument(
    "filename",
    nargs="?",
    default="sales_new.csv",
    help="Source CSV filename"
)

parser.add_argument(
    "--db-path",
    default=str(DEFAULT_DB_PATH),
    help="Target SQLite database path"
)

parser.add_argument(
    "--output-dir",
    default=str(PROCESSED_DIR),
    help="Directory containing validated CSV files and loading summaries"
)

parser.add_argument(
    "--quarantine-dir",
    default=str(QUARANTINE_DIR),
    help="Directory for conflicting transaction reports"
)


args = parser.parse_args()

filename = args.filename
DB_PATH = resolve_project_path(args.db_path)
OUTPUT_DIR = resolve_project_path(args.output_dir)
QUARANTINE_OUTPUT_DIR = resolve_project_path(args.quarantine_dir)


INCOMING_PATH = (
    OUTPUT_DIR / f"{Path(filename).stem}_accepted.csv"
)


COLUMNS = ["Sale_ID", "Date", "Store_ID", "Product_ID", "Units"]

def read_rows(path):
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(
        df["Date"], format="%Y-%m-%d"
    ).dt.strftime("%Y-%m-%d")

    return list(df[COLUMNS].itertuples(index=False, name=None))


if not DB_PATH.is_file():
    raise FileNotFoundError(
        f"Database not found: {DB_PATH}. "
        "Database initialization is required."
    )


conn = sqlite3.connect(DB_PATH)

try:
    
    # Verify that the database was initialized
    # and contains the required sales columns.
    try:
        conn.execute("""
            SELECT
                Sale_ID,
                Date,
                Store_ID,
                Product_ID,
                Units
            FROM sales
            LIMIT 0
        """)
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Database schema is missing or incompatible. "
            "Database initialization is required."
        ) from exc



    # Read validated incoming sales
    incoming = read_rows(INCOMING_PATH)

    # Find previously stored transactions in batches
    existing = {}

    for i in range(0, len(incoming), 500):
        batch = incoming[i:i + 500]
        ids = [row[0] for row in batch]

        placeholders = ",".join("?" * len(ids))

        query = (
            "SELECT Sale_ID, Date, Store_ID, Product_ID, Units "
            f"FROM sales WHERE Sale_ID IN ({placeholders})"
        )

        for row in conn.execute(query, ids):
            existing[row[0]] = row

    new_rows = []
    already_present = 0
    conflicts = []

    for row in incoming:
        sale_id = row[0]

        if sale_id not in existing:
            new_rows.append(row)
        elif row == existing[sale_id]:
            already_present += 1
        else:
            conflicts.append(row)

    # Do not silently overwrite conflicting transactions
    
    if conflicts:
        conflict_records = []

        for incoming_row in conflicts:
            stored_row = existing[incoming_row[0]]

            record = {
                "Sale_ID": incoming_row[0],
                "Error_Reason": "Conflicting existing transaction"
            }

            for i, column in enumerate(COLUMNS[1:], start=1):
                record[f"Stored_{column}"] = stored_row[i]
                record[f"Incoming_{column}"] = incoming_row[i]

            conflict_records.append(record)

        quarantine_dir = QUARANTINE_OUTPUT_DIR
        quarantine_dir.mkdir(parents=True, exist_ok=True)

        report_path = (
            quarantine_dir
            / f"{Path(filename).stem}_conflicts.csv"
        )

        pd.DataFrame(conflict_records).to_csv(
            report_path, index=False
        )

        raise ValueError(
            f"{len(conflicts)} conflicting transactions found. "
            f"Report saved to: {report_path}. "
            "No new transactions were inserted."
        )


    # Insert only genuinely new records
    with conn:
        conn.executemany(
            "INSERT INTO sales VALUES (?, ?, ?, ?, ?)",
            new_rows
        )

    total = conn.execute(
        "SELECT COUNT(*) FROM sales"
    ).fetchone()[0]

    print("\n=== INCREMENTAL LOAD ===")
    print(f"New records inserted: {len(new_rows):,}")
    print(f"Already present: {already_present:,}")
    print(f"Total database records: {total:,}")

    
    # Save structured loading results
    load_summary = {
        "source_file": filename,
        "loaded_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "new_records": int(len(new_rows)),
        "already_present": int(already_present),
        "total_database_records": int(total),
        "load_status": "SUCCESS"
    }

    summary_dir = OUTPUT_DIR
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary_path = (
        summary_dir / f"{Path(filename).stem}_load_summary.json"
    )

    summary_path.write_text(
        json.dumps(
            load_summary,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )


finally:
    conn.close()
