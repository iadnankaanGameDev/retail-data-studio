import os
from pathlib import Path
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from desktop import MainWindow
from projects import Project
from test_reporting import sample_project


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def wait_for_report(app, view):
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(1)
    deadline = time.monotonic() + 15
    while view.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.002)
    timer.stop()
    assert not view.busy
    return ticks


def test_reports_background_filter_export_and_project_switch(app, sample_project, monkeypatch):
    import reports_view
    real_query = reports_view.query_report

    def slower_query(*args):
        time.sleep(0.08)
        return real_query(*args)

    monkeypatch.setattr(reports_view, "query_report", slower_query)
    missing = Project("missing", "Missing Demo", sample_project.root, "Missing", "missing.db")
    window = MainWindow((sample_project, missing))
    view = window.reports
    view.load_report()
    assert not window.project_box.isEnabled()
    assert not window.start_button.isEnabled()
    assert wait_for_report(app, view), "UI timer must run while report is queried"
    assert view.result is not None, view.status.text()
    assert view.chart_view.mode == "bar"
    assert len(view.chart_view.bars) > 0
    assert view.models["stores"].rowCount() == 2
    view.category.setCurrentText("Toys")
    assert view.result is None
    assert not view.export.isEnabled()
    view.load_report()
    wait_for_report(app, view)
    assert view.result.totals["Transactions"] == 4
    view.export_current()
    wait_for_report(app, view)
    assert (view.export_folder / "periods.csv").is_file()
    window.project_box.setCurrentIndex(1)
    assert view.result is None and not view.open_export.isEnabled()
    assert "Missing Demo" in window.database_label.text()
    assert not missing.database.exists()
    view.load_report()
    wait_for_report(app, view)
    assert "bulunamadı" in view.status.text()
    assert not view.export.isEnabled()
    window.close()
