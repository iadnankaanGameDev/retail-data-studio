"""All databases and catalogues in these tests are synthetic and temporary."""
from contextlib import closing
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from projects import Project, PROJECTS
from reporting import ReportFilter, date_range, query_report, open_readonly, export_report


@pytest.fixture
def sample_project(tmp_path):
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/database").mkdir()
    (tmp_path / "data/raw/products.csv").write_text(
        "Product_ID,Product_Category,Product_Price\n10,Toys,$2.35\n20,Games,$10.00\n", encoding="utf-8")
    (tmp_path / "data/raw/stores.csv").write_text(
        "Store_ID,Store_Name\n1,Ankara\n2,İzmir\n", encoding="utf-8")
    project = Project("demo", "Test Demo", tmp_path, "Synthetic",
                      "data/database/customer_demo.db", "data/processed/customer_demo")
    with closing(sqlite3.connect(project.database)) as connection:
        connection.execute("CREATE TABLE sales (Sale_ID INTEGER PRIMARY KEY, Date TEXT, "
                           "Store_ID INTEGER, Product_ID INTEGER, Units INTEGER)")
        connection.executemany("INSERT INTO sales VALUES (?, ?, ?, ?, ?)", [
            (1, "2023-12-31", 1, 10, 2), (2, "2024-01-01", 1, 20, 3),
            (3, "2024-01-07", 2, 10, 4), (4, "2024-01-08", 1, 10, 1),
            (5, "2024-03-31", 2, 20, 2), (6, "2024-04-01", 1, 20, 1),
            (7, "2025-01-01", 2, 10, 2),
        ])
        connection.commit()
    return project


def test_totals_filters_and_readonly(sample_project):
    before = hashlib.sha256(sample_project.database.read_bytes()).digest()
    result = query_report(sample_project, ReportFilter())
    assert result.totals == {"Transactions": 7, "Units_Sold": 15, "Estimated Revenue": 81.15}
    for frame in (result.periods, result.categories, result.stores):
        assert frame.Transactions.sum() == 7
        assert frame.Units_Sold.sum() == 15
        assert frame["Estimated Revenue"].sum() == pytest.approx(81.15)
    filtered = query_report(sample_project, ReportFilter(
        date(2024, 1, 1), date(2024, 1, 8), "Haftalık", 1, "Toys"))
    assert filtered.totals == {"Transactions": 1, "Units_Sold": 1, "Estimated Revenue": 2.35}
    assert filtered.periods.Period.tolist() == ["2024-01-08"]
    boundary = query_report(sample_project, ReportFilter(date(2024, 1, 1), date(2024, 1, 7)))
    assert boundary.totals["Transactions"] == 2
    with closing(open_readonly(sample_project.database)) as connection:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM sales")
    assert hashlib.sha256(sample_project.database.read_bytes()).digest() == before


@pytest.mark.parametrize("grouping,periods", [
    ("Günlük", ["2023-12-31", "2024-01-01", "2024-01-07", "2024-01-08", "2024-03-31", "2024-04-01", "2025-01-01"]),
    ("Haftalık", ["2023-12-25", "2024-01-01", "2024-01-08", "2024-03-25", "2024-04-01", "2024-12-30"]),
    ("Aylık", ["2023-12-01", "2024-01-01", "2024-03-01", "2024-04-01", "2025-01-01"]),
    ("Üç aylık", ["2023-10-01", "2024-01-01", "2024-04-01", "2025-01-01"]),
    ("Yıllık", ["2023-01-01", "2024-01-01", "2025-01-01"]),
])
def test_groupings_are_independent_of_date_range(sample_project, grouping, periods):
    result = query_report(sample_project, ReportFilter(grouping=grouping))
    assert result.periods.Period.tolist() == periods
    assert result.totals["Transactions"] == 7


@pytest.mark.parametrize("preset,start,end", [
    ("Son 7 gün", date(2024, 2, 24), date(2024, 3, 1)),
    ("Bu ay", date(2024, 3, 1), date(2024, 3, 1)),
    ("Son 3 ay", date(2023, 12, 2), date(2024, 3, 1)),
    ("Son 12 ay", date(2023, 3, 2), date(2024, 3, 1)),
    ("Bu yıl", date(2024, 1, 1), date(2024, 3, 1)),
    ("Tüm zamanlar", None, None),
])
def test_presets(preset, start, end):
    assert date_range(preset, date(2024, 3, 1)) == (start, end)


def test_rolling_month_clamps_leap_day():
    assert date_range("Son 12 ay", date(2024, 2, 29)) == (date(2023, 3, 1), date(2024, 2, 29))


def test_empty_invalid_and_missing_database(sample_project):
    result = query_report(sample_project, ReportFilter(category="absent"))
    assert result.totals == {"Transactions": 0, "Units_Sold": 0, "Estimated Revenue": 0.0}
    assert result.periods.empty and result.categories.empty and result.stores.empty
    result = query_report(sample_project, ReportFilter(date(2090, 1, 1), date(2090, 1, 2)))
    assert result.totals["Transactions"] == 0
    with pytest.raises(ValueError, match="Başlangıç"):
        query_report(sample_project, ReportFilter(date(2025, 1, 1), date(2024, 1, 1)))
    missing = Project("missing", "Missing", sample_project.root, "Missing", "missing.db")
    with pytest.raises(FileNotFoundError):
        query_report(missing, ReportFilter())
    assert not missing.database.exists()


def test_bad_catalog_is_not_silently_ignored(sample_project):
    path = sample_project.root / "data/raw/products.csv"
    path.write_text("Product_ID,Product_Category,Product_Price\n10,Toys,broken\n")
    with pytest.raises(ValueError, match="fiyat"):
        query_report(sample_project, ReportFilter())
    path.write_text("Product_ID,Product_Category,Product_Price\n10,Toys,$2.35\n")
    with pytest.raises(ValueError, match="eşleşmeyen"):
        query_report(sample_project, ReportFilter())


def test_export_matches_filtered_snapshot(sample_project):
    filters = ReportFilter(date(2024, 1, 1), date(2024, 1, 8), "Haftalık", category="Toys")
    result = query_report(sample_project, filters)
    folder = export_report(result, sample_project.output_root)
    assert folder.is_relative_to(sample_project.output_root)
    for name, frame in (("periods", result.periods), ("categories", result.categories), ("stores", result.stores)):
        exported = pd.read_csv(folder / f"{name}.csv")
        pd.testing.assert_frame_equal(exported, frame, check_dtype=False)
    assert pd.read_csv(folder / "totals.csv")["Transactions"].iloc[0] == 2
    metadata = json.loads((folder / "filters.json").read_text(encoding="utf-8"))
    assert metadata["database"] == str(sample_project.database)
    assert metadata["filters"]["start"] == "2024-01-01"
    assert metadata["filters"]["grouping"] == "Haftalık"


def test_production_and_demo_profiles_are_separate():
    production, demo = PROJECTS
    assert production.database.name == "sales.db"
    assert demo.database.name == "customer_demo.db"
    assert production.output_root != demo.output_root
    assert demo.output_root.parts[-2:] == ("processed", "customer_demo")
