"""Project creation, persistence and real pipeline isolation with temporary data."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from project_manager import create_project, load_projects
from reporting import query_report, ReportFilter


@pytest.fixture
def catalogs(tmp_path):
    products, stores = tmp_path / "ürünler.csv", tmp_path / "mağazalar.csv"
    products.write_text("Product_ID,Product_Category,Product_Price,Product_Cost\n9001,Özel,12.50,4.00\n", encoding="utf-8")
    stores.write_text("Store_ID,Store_Name\n8001,Özel mağaza\n", encoding="utf-8")
    return products, stores


def test_create_persist_load_three_sales_and_isolate(tmp_path, catalogs):
    store = tmp_path / "projeler"
    products, stores = catalogs
    originals = (products.read_bytes(), stores.read_bytes())
    first = create_project("Birinci proje", products, stores, store)
    assert (products.read_bytes(), stores.read_bytes()) == originals
    products.write_text("Product_ID,Product_Category,Product_Price,Product_Cost\n9001,Diğer,99.00,8.00\n", encoding="utf-8")
    second = create_project("İkinci proje", products, stores, store)
    second_before = second.database.read_bytes()
    with closing(sqlite3.connect(first.database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0
    for folder in (first.incoming_dir, first.reference_dir, first.output_root, first.quarantine_dir):
        assert folder.is_dir()
    assert first.entrypoint == ROOT / "src/main.py"
    assert second.database != first.database
    assert originals[1] == stores.read_bytes()
    assert "12.50" in (first.reference_dir / "products.csv").read_text(encoding="utf-8-sig")
    source = first.incoming_dir / "üç satış.csv"
    source.write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n"
                      "1,2024-01-01,8001,9001,1\n2,2024-01-02,8001,9001,2\n"
                      "3,2024-01-03,8001,9001,3\n", encoding="utf-8")
    for number, expected in ((1, 3), (2, 0)):
        output = first.output_root / str(number)
        result = subprocess.run([
            sys.executable, str(first.entrypoint), source.name,
            "--incoming-dir", str(first.incoming_dir), "--reference-dir", str(first.reference_dir),
            "--db-path", str(first.database), "--output-dir", str(output),
            "--quarantine-dir", str(first.quarantine_dir / str(number)),
            "--log-dir", str(output / "logs"),
        ], cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert result.returncode == 0, result.stdout + result.stderr
        summary = json.loads((output / "üç satış_load_summary.json").read_text(encoding="utf-8"))
        assert summary["new_records"] == expected
        assert (output / "store_daily_summary.csv").exists()
    result = query_report(first, ReportFilter())
    assert result.totals == {"Transactions": 3, "Units_Sold": 6, "Estimated Revenue": 75.0}
    assert second.database.read_bytes() == second_before
    loaded, errors = load_projects(store)
    assert errors == []
    assert {p.key for p in loaded} == {first.key, second.key}
    restored = next(p for p in loaded if p.key == first.key)
    assert query_report(restored, ReportFilter()).totals == result.totals


def test_invalid_catalog_does_not_publish_project(tmp_path, catalogs):
    products, stores = catalogs
    products.write_text("Product_ID,Product_Price\n1,$2.00\n")
    with pytest.raises(ValueError, match="Eksik"):
        create_project("Invalid", products, stores, tmp_path / "projects")
    assert load_projects(tmp_path / "projects") == ([], [])


def test_config_errors_are_visible_and_missing_db_not_recreated(tmp_path, catalogs):
    project = create_project("Project", *catalogs, tmp_path / "projects")
    config_path = project.root / "project.json"
    original = config_path.read_text(encoding="utf-8")
    config = json.loads(original)
    config["paths"]["database"] = "../other.db"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    loaded, errors = load_projects(tmp_path / "projects")
    assert not loaded and errors
    config_path.write_text("[]", encoding="utf-8")
    assert load_projects(tmp_path / "projects")[1]
    config = json.loads(original)
    config["template"] = "unsupported_schema"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    assert load_projects(tmp_path / "projects")[1]
    config_path.write_text(original, encoding="utf-8")
    project.database.unlink()  # Only this test's temporary database.
    loaded, errors = load_projects(tmp_path / "projects")
    assert len(loaded) == 1 and not errors
    assert not project.database.exists()


def test_failed_creation_is_not_registered(tmp_path, catalogs, monkeypatch):
    import project_manager
    def fail(_):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(project_manager, "initialize_database", fail)
    with pytest.raises(OSError, match="disk failure"):
        create_project("Project", *catalogs, tmp_path / "projects")
    assert list((tmp_path / "projects").iterdir()) == []
