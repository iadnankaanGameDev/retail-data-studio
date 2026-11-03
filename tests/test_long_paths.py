"""Exercise >260 character paths, real subprocess ETL, SQLite and persistence."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from filesystem import fs_path, display_path
from project_manager import create_project, load_projects
from reporting import query_report, ReportFilter, export_report, open_readonly
from test_project_manager import catalogs
from test_desktop import app, run_window
from desktop import MainWindow


def deep_root(tmp_path):
    path = tmp_path / "Türkçe klasör boşluk"
    while len(str(path)) < 290:
        path /= "nested-project-data-0123456789"
    return path


def test_long_project_etl_reports_and_reopen(tmp_path, catalogs, app):
    store = deep_root(tmp_path) / "projects"
    project = create_project("Long path", *catalogs, store)
    other = create_project("Isolated", *catalogs, store)
    untouched = fs_path(other.database).read_bytes()
    assert len(str(project.database)) > 260
    source = project.incoming_dir / "üç satış.csv"
    fs_path(source).write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n"
                              "1,2024-01-01,8001,9001,1\n2,2024-01-02,8001,9001,2\n"
                              "3,2024-01-03,8001,9001,3\n4,bad-date,8001,9001,1\n", encoding="utf-8")
    window = MainWindow((project,))
    try:
        for expected in (3, 0):
            run_window(app, window, source)
            assert "Tamamlandı" in window.status_label.text(), window.log.toPlainText()
            assert window.metrics["new_records"].text() == str(expected)
            assert window.metrics["validation_rejected"].text() == "1"
            assert list(fs_path(window.output_dir / "run_summaries").glob("*.json"))
        assert list(fs_path(project.quarantine_dir).rglob("*_rejected.csv"))
    finally:
        window.close()
    loaded, errors = load_projects(store)
    assert not errors and len(loaded) == 2
    restored = next(p for p in loaded if p.key == project.key)
    result = query_report(restored, ReportFilter())
    assert result.totals == {"Transactions": 3, "Units_Sold": 6, "Estimated Revenue": 75.0}
    folder = export_report(result, project.output_root)
    assert len(str(folder / "totals.csv")) > 260
    assert "75.00" in fs_path(folder / "totals.csv").read_text(encoding="utf-8-sig")
    assert fs_path(other.database).read_bytes() == untouched
    with open_readonly(project.database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM sales")


def test_long_error_log_and_missing_db_readonly(tmp_path, catalogs):
    project = create_project("Failure logging", *catalogs, deep_root(tmp_path))
    output = project.output_root / "failed-run"
    result = subprocess.run([sys.executable, str(project.entrypoint), "missing.csv",
        "--incoming-dir", str(project.incoming_dir), "--reference-dir", str(project.reference_dir),
        "--db-path", str(project.database), "--output-dir", str(output),
        "--log-dir", str(output / "logs")], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=90)
    assert result.returncode != 0
    assert "missing.csv" in fs_path(output / "logs/last_error.log").read_text(encoding="utf-8")
    summaries = list(fs_path(output / "run_summaries").glob("*.json"))
    assert len(summaries) == 1
    assert json.loads(summaries[0].read_text(encoding="utf-8"))["status"] == "FAILED"
    missing = project.database.with_name("does-not-exist.db")
    with pytest.raises(sqlite3.OperationalError):
        open_readonly(missing)
    assert not fs_path(missing).exists()


def test_extended_path_roundtrip(tmp_path):
    path = tmp_path / "folder" / ".." / "file.csv"
    normalized = tmp_path / "file.csv"
    assert display_path(fs_path(path)) == normalized
    assert fs_path(fs_path(path)) == fs_path(path)
