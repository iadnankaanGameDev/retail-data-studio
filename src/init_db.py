
from pathlib import Path
import argparse
import sqlite3
from filesystem import fs_path

BASE_DIR = Path(__file__).resolve().parent.parent


def initialize_database(db_path):
    db_path = fs_path(db_path)
    # Never overwrite an existing database
    if db_path.exists():
        raise SystemExit(
            f"[ERROR] Database already exists: {db_path}"
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)

    try:
        with conn:
            conn.execute("""
                CREATE TABLE sales (
                    Sale_ID INTEGER PRIMARY KEY,
                    Date TEXT NOT NULL,
                    Store_ID INTEGER NOT NULL,
                    Product_ID INTEGER NOT NULL,
                    Units INTEGER NOT NULL CHECK (Units > 0)
                )
            """)

        count = conn.execute(
            "SELECT COUNT(*) FROM sales"
        ).fetchone()[0]

        print("\n=== DATABASE INITIALIZATION ===")
        print(f"Database created: {db_path}")
        print(f"Initial sales records: {count}")
        print("Database initialization: SUCCESS")

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--db-path",
        required=True,
        help="Location of the new SQLite database"
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)

    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    initialize_database(db_path)
