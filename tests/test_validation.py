
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd


def test_invalid_sales_are_quarantined(tmp_path):
    # Create an isolated test environment
    root = tmp_path

    for folder in [
        "src",
        "data/raw",
        "data/incoming"
    ]:
        (root / folder).mkdir(parents=True, exist_ok=True)

    # Copy our real validation script
    project_root = Path(__file__).resolve().parent.parent
    shutil.copy2(project_root / "src/filesystem.py", root / "src/filesystem.py")

    shutil.copy2(
        project_root / "src/process_incoming.py",
        root / "src/process_incoming.py"
    )
    shutil.copy2(
        project_root / "src/paths.py",
        root / "src/paths.py"
    )

    # Create small reference tables
    (root / "data/raw/products.csv").write_text(
        "Product_ID\n10\n",
        encoding="utf-8"
    )

    (root / "data/raw/stores.csv").write_text(
        "Store_ID\n1\n",
        encoding="utf-8"
    )

    # Create a test batch with intentional errors
    (root / "data/incoming/test_sales.csv").write_text(
        "Sale_ID,Date,Store_ID,Product_ID,Units\n"
        "1,2023-10-01,1,10,2\n"
        "2,invalid-date,1,10,3\n"
        "3,2023-10-01,1,9999,1\n",
        encoding="utf-8"
    )

    # Execute the real validation script
    subprocess.run(
        [
            sys.executable,
            str(root / "src/process_incoming.py"),
            "test_sales.csv"
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True
    )

    accepted = pd.read_csv(
        root / "data/processed/test_sales_accepted.csv"
    )

    rejected = pd.read_csv(
        root / "data/quarantine/test_sales_rejected.csv"
    )

    # Verify results automatically
    assert len(accepted) == 1
    assert len(rejected) == 2

    assert accepted["Sale_ID"].tolist() == [1]

    reasons = dict(
        zip(rejected["Sale_ID"], rejected["Error_Reason"])
    )

    assert "Invalid date" in reasons[2]
    assert "Invalid Product_ID" in reasons[3]
