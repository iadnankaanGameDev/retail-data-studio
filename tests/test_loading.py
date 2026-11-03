
from pathlib import Path
from contextlib import closing
import shutil
import sqlite3
import subprocess
import sys


def test_incremental_loading_is_idempotent(tmp_path):
    root = tmp_path

    # Create an isolated project structure
    for folder in [
        "src",
        "data/database",
        "data/processed"
    ]:
        (root / folder).mkdir(parents=True, exist_ok=True)

    # Copy the actual loading module
    project_root = Path(__file__).resolve().parent.parent
    shutil.copy2(project_root / "src/filesystem.py", root / "src/filesystem.py")

    shutil.copy2(
        project_root / "src/load_sales.py",
        root / "src/load_sales.py"
    )
    shutil.copy2(
        project_root / "src/paths.py",
        root / "src/paths.py"
    )
    
    db_path = root / "data/database/sales.db"

    # Create a small test database with one sale
    with closing(sqlite3.connect(db_path)) as conn:
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

            conn.execute(
                "INSERT INTO sales VALUES (?, ?, ?, ?, ?)",
                (1, "2023-10-01", 1, 10, 2)
            )

    # One existing sale and one new sale
    incoming_path = (
        root / "data/processed/test_sales_accepted.csv"
    )

    incoming_path.write_text(
        "Sale_ID,Date,Store_ID,Product_ID,Units\n"
        "1,2023-10-01,1,10,2\n"
        "2,2023-10-02,1,10,4\n",
        encoding="utf-8"
    )

    def run_loader(check=True):
        return subprocess.run(
            [
                sys.executable,
                str(root / "src/load_sales.py"),
                "test_sales.csv"
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=check
        )

    # First run: insert one new sale
    first = run_loader()

    assert "New records inserted: 1" in first.stdout
    assert "Already present: 1" in first.stdout

    # Second run: do not insert duplicates
    second = run_loader()

    assert "New records inserted: 0" in second.stdout
    assert "Already present: 2" in second.stdout

    # Verify the final database contents
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT Sale_ID, Units FROM sales ORDER BY Sale_ID"
        ).fetchall()

    assert rows == [(1, 2), (2, 4)]
    
    # Test a conflicting transaction and a new transaction
    incoming_path.write_text(
        "Sale_ID,Date,Store_ID,Product_ID,Units\n"
        "2,2023-10-02,1,10,99\n"
        "3,2023-10-03,1,10,5\n",
        encoding="utf-8"
    )

    # Failure is expected for this batch
    conflict_result = run_loader(check=False)

    assert conflict_result.returncode != 0
    assert "conflicting transactions" in conflict_result.stderr

    # Confirm that neither transaction changed the database
    with closing(sqlite3.connect(db_path)) as conn:
        rows_after_conflict = conn.execute(
            "SELECT Sale_ID, Units FROM sales ORDER BY Sale_ID"
        ).fetchall()

    assert rows_after_conflict == [(1, 2), (2, 4)]

    # Verify that the conflict report was created
    conflict_report = (
        root / "data/quarantine/test_sales_conflicts.csv"
    )

    assert conflict_report.exists()
    assert "Conflicting existing transaction" in (
        conflict_report.read_text(encoding="utf-8")
    )

