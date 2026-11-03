"""Exercise the real Qt process bridge against an isolated Toy Sales project."""
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time
from contextlib import closing

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from desktop import MainWindow
from projects import Project


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "örnek proje"
    original = Path(__file__).resolve().parents[1]
    shutil.copytree(original / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    (root / "data/raw").mkdir(parents=True)
    (root / "data/database").mkdir()
    (root / "data/raw/products.csv").write_text(
        "Product_ID,Product_Price,Product_Cost,Product_Category\n10,$5.00,$2.00,Toys\n")
    (root / "data/raw/stores.csv").write_text("Store_ID,Store_Name\n1,Test Store\n")
    p = Project("test", "Test Toy Sales", root, "Isolated test")
    with closing(sqlite3.connect(p.database)) as connection:
        connection.execute("CREATE TABLE sales (Sale_ID INTEGER PRIMARY KEY, Date TEXT, "
                           "Store_ID INTEGER, Product_ID INTEGER, Units INTEGER)")
        connection.commit()
    return p


def run_window(app, window, source):
    window.file_edit.setText(str(source))
    window.start_processing()
    assert window.process is not None
    assert not window.start_button.isEnabled()
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)
    deadline = time.monotonic() + 60
    while window.process is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    timer.stop()
    assert window.process is None, "ETL did not finish within 60 seconds"
    assert ticks, "UI event loop was not responsive during ETL"
    assert window.start_button.isEnabled()


def test_pipeline_success_repeat_conflict_and_invalid_file(app, project, tmp_path):
    source = tmp_path / "satış verisi.csv"
    source.write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n"
                      "1,2023-10-01,1,10,2\n2,bad-date,1,10,2\n", encoding="utf-8")
    window = MainWindow((project,))
    run_window(app, window, source)
    assert "Tamamlandı" in window.status_label.text(), window.log.toPlainText()
    assert window.metrics["validation_accepted"].text() == "1"
    assert window.metrics["validation_rejected"].text() == "1"
    assert window.metrics["new_records"].text() == "1"
    first_output = window.output_dir
    assert (first_output / "store_daily_summary.csv").is_file()
    run_window(app, window, source)
    assert window.metrics["new_records"].text() == "0"
    assert window.metrics["already_present"].text() == "1"
    assert window.output_dir != first_output

    source.write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n"
                      "1,2023-10-01,1,10,99\n3,2023-10-01,1,10,4\n")
    run_window(app, window, source)
    assert "başarısız" in window.status_label.text()
    assert "conflicting transactions" in window.log.toPlainText()
    assert window.metrics["validation_accepted"].text() == "2"
    assert window.metrics["new_records"].text() == "—"
    with closing(sqlite3.connect(project.database)) as connection:
        assert connection.execute("SELECT Sale_ID, Units FROM sales").fetchall() == [(1, 2)]

    source.write_text("wrong_column\nvalue\n")
    run_window(app, window, source)
    assert "başarısız" in window.status_label.text()
    assert "Missing required columns" in window.log.toPlainText()
    assert window.metrics["validation_accepted"].text() == "—"
    window.close()


def test_missing_input_and_database_do_not_start_process(app, project, tmp_path):
    window = MainWindow((project,))
    window.file_edit.setText(str(tmp_path / "missing.csv"))
    window.start_processing()
    assert window.process is None
    source = tmp_path / "input.csv"
    source.write_text("Sale_ID\n")
    project.database.unlink()  # This fixture is always under pytest's temporary directory.
    window.file_edit.setText(str(source))
    window.start_processing()
    assert window.process is None
    assert "Veritabanı bulunamadı" in window.status_label.text()
    assert not project.database.exists()
    window.close()


def test_report_failure_preserves_loading_counts(app, project, tmp_path):
    # Validation needs only Product_ID; reports need the other product columns.
    (project.root / "data/raw/products.csv").write_text("Product_ID\n10\n")
    source = tmp_path / "valid.csv"
    source.write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n1,2023-10-01,1,10,2\n")
    window = MainWindow((project,))
    run_window(app, window, source)
    assert "başarısız" in window.status_label.text()
    assert "geri almaz" in window.status_label.text()
    assert window.metrics["new_records"].text() == "1"
    assert window.progress.value() == 2
    with closing(sqlite3.connect(project.database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 1
    window.close()


def test_failed_start_releases_controls(app, project, tmp_path, monkeypatch):
    source = tmp_path / "valid.csv"
    source.write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "missing-python.exe"))
    window = MainWindow((project,))
    window.file_edit.setText(str(source))
    window.start_processing()
    deadline = time.monotonic() + 10
    while window.process is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert window.process is None
    assert window.start_button.isEnabled()
    assert "başlatılamadı" in window.status_label.text()
    window.close()


def test_close_is_blocked_while_processing(app, project, monkeypatch):
    window = MainWindow((project,))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    window.process = object()
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()
    window.process = None
    window.close()


def test_demo_etl_never_writes_production_database(app, project, tmp_path):
    from dataclasses import replace
    demo = replace(project, key="demo", name="Toy Sales Demo",
                   database_relative="data/database/customer_demo.db",
                   output_relative="data/processed/customer_demo")
    production_before = project.database.read_bytes()
    with closing(sqlite3.connect(demo.database)) as connection:
        connection.execute("CREATE TABLE sales (Sale_ID INTEGER PRIMARY KEY, Date TEXT, "
                           "Store_ID INTEGER, Product_ID INTEGER, Units INTEGER)")
        connection.commit()
    source = tmp_path / "demo.csv"
    source.write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n1,2023-10-01,1,10,2\n")
    window = MainWindow((project, demo))
    window.project_box.setCurrentIndex(1)
    run_window(app, window, source)
    assert "Tamamlandı" in window.status_label.text(), window.log.toPlainText()
    assert window.output_dir.is_relative_to(demo.output_root)
    assert "customer_demo.db" in window.database_label.text()
    assert project.database.read_bytes() == production_before
    with closing(sqlite3.connect(demo.database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 1
    window.close()


def test_missing_demo_does_not_fall_back_to_production(app, project, tmp_path):
    from dataclasses import replace
    demo = replace(project, key="demo", name="Toy Sales Demo",
                   database_relative="data/database/customer_demo.db",
                   output_relative="data/processed/customer_demo")
    production_before = project.database.read_bytes()
    source = tmp_path / "demo.csv"
    source.write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n1,2023-10-01,1,10,2\n")
    window = MainWindow((project, demo))
    window.project_box.setCurrentIndex(1)
    window.file_edit.setText(str(source))
    window.start_processing()
    assert window.process is None
    assert "Veritabanı bulunamadı" in window.status_label.text()
    assert not demo.database.exists()
    assert project.database.read_bytes() == production_before
    window.close()
