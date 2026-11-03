"""File-only simulation tests. No database creation or loading."""
import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("daily_demo", ROOT / "scripts/generate_daily_sales_demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.fixture
def references(tmp_path):
    folder = tmp_path / "references"
    folder.mkdir()
    (folder / "products.csv").write_text(
        "Product_ID,Product_Category,Product_Price\n1,Toys,$12.50\n2,Games,$5.99\n", encoding="utf-8")
    (folder / "stores.csv").write_text(
        "Store_ID,Store_Name,Store_Location\n1,One,Downtown\n2,Two,Residential\n", encoding="utf-8")
    return folder


def test_reproducible_and_no_reference_changes(tmp_path, references):
    original = {p.name: p.read_bytes() for p in references.iterdir()}
    first, second = tmp_path / "a", tmp_path / "b"
    report = demo.write_dataset(first, references)
    demo.write_dataset(second, references)
    snapshot = {p.name: p.read_bytes() for p in first.iterdir()}
    assert snapshot == {p.name: p.read_bytes() for p in second.iterdir()}
    demo.write_dataset(first, references)
    assert snapshot == {p.name: p.read_bytes() for p in first.iterdir()}
    assert original == {p.name: p.read_bytes() for p in references.iterdir()}
    assert report["days"] == 87 and report["sales_files"] == 8
    assert report["weekend_mean"] > report["weekday_mean"]
    assert len(list(first.glob("sales_*.csv"))) == 8
    assert len(list(first.glob("expected_*.csv"))) == 9
    assert not list(tmp_path.rglob("*.db"))


@pytest.mark.parametrize("field,value,error", [
    ("Sale_ID", "duplicate", "Duplicate Sale_ID"),
    ("Date", "2026-10-19", "Date out of range"),
    ("Product_ID", "999999", "Invalid reference"),
    ("Store_ID", "999999", "Invalid reference"),
    ("Units", "0", "Invalid Units"),
    ("Units", "", "Missing field"),
])
def test_validator_rejects_corruption(tmp_path, references, field, value, error):
    output = tmp_path / "out"
    demo.write_dataset(output, references)
    file = output / "sales_2026-10-20.csv"
    columns, rows = demo.read_csv(file)
    rows[0][field] = rows[1][field] if value == "duplicate" else value
    file.write_bytes(demo.csv_bytes(columns, rows))
    products, stores, _ = demo.catalogs(references)
    with pytest.raises(ValueError, match=error):
        demo.validate(output, products, stores)
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        demo.write_dataset(output, references)


def test_expected_totals_and_columns_are_checked(tmp_path, references):
    output = tmp_path / "out"
    demo.write_dataset(output, references)
    products, stores, _ = demo.catalogs(references)
    target = output / "expected_monthly.csv"
    columns, rows = demo.read_csv(target)
    rows[0]["Transactions"] = str(int(rows[0]["Transactions"]) + 1)
    target.write_bytes(demo.csv_bytes(columns, rows))
    with pytest.raises(ValueError, match="summary mismatch"):
        demo.validate(output, products, stores)
    sales = output / "sales_2026-10-26.csv"
    sales.write_text("wrong_column\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Incorrect columns"):
        demo.validate(output, products, stores)


def test_generator_does_not_overwrite_unowned_files(tmp_path, references):
    output = tmp_path / "out"
    output.mkdir()
    target = output / "sales_history_seed.csv"
    target.write_text("user file", encoding="utf-8")
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        demo.write_dataset(output, references)
    assert target.read_text() == "user file"
