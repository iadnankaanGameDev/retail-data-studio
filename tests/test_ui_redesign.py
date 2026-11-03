"""Widget behavior and small-window layout; all report data is synthetic."""
from datetime import date
import os
from pathlib import Path
import sys

import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStackedWidget

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from desktop import MainWindow, STYLE
from reporting import query_report, ReportFilter
from test_reports_view import app
from test_reporting import sample_project


def test_navigation_and_compact_layout(app, sample_project):
    app.setStyleSheet(STYLE)
    window = MainWindow((sample_project,))
    window.resize(910, 512)  # Approximate logical area of 1366x768 at 150%.
    window.show()
    window.nav_items[1].click()
    app.processEvents()
    app.processEvents()  # Adaptive grids request a second layout pass.
    assert isinstance(window.pages, QStackedWidget)
    assert window.pages.currentIndex() == 1
    assert window.nav_items[1].isChecked() and not window.nav_items[0].isChecked()
    assert window.reports.kpi_grid.columns == 2
    scroll = window.pages.currentWidget()
    assert scroll.horizontalScrollBar().maximum() == 0
    assert scroll.verticalScrollBar().maximum() > 0
    assert window.width() == 910 and window.height() == 512
    assert str(sample_project.root) not in window.database_label.text()
    assert window.database_label.toolTip() == str(sample_project.database)
    window.close()


def test_single_period_is_bar_and_metrics_are_real(app, sample_project):
    window = MainWindow((sample_project,))
    view = window.reports
    result = query_report(sample_project, ReportFilter(date(2024, 1, 1), date(2024, 1, 7)))
    view.show_result(result)
    assert view.chart_view.mode == "bar"
    assert view.chart_view.bars[0].get_height() == pytest.approx(39.4)
    assert view.kpis["Active Stores"].text() == "2"
    assert view.kpis["Estimated Revenue"].text() == "$39.40"
    assert [label.get_text() for label in view.chart_view.axes.get_xticklabels()] == ["Jan 2024"]
    view.chart_metric.setCurrentIndex(view.chart_metric.findData("Units_Sold"))
    assert view.chart_view.bars[0].get_height() == 7
    view.chart_metric.setCurrentIndex(view.chart_metric.findData("Transactions"))
    assert view.chart_view.bars[0].get_height() == 2
    view.show_result(query_report(sample_project, ReportFilter(category="not found")))
    assert not view.empty_state.isHidden()
    assert view.chart_view.isHidden()
    assert view.kpis["Active Stores"].text() == "0"
    assert "bulunamadı" in view.empty_message.text()
    window.close()


def test_long_series_and_numeric_table_sort(app, sample_project):
    window = MainWindow((sample_project,))
    view = window.reports
    result = query_report(sample_project, ReportFilter())
    # Synthetic rendering-only series; no changes to any database.
    result.periods = pd.DataFrame({"Period": pd.date_range("2024-01-01", periods=20).strftime("%Y-%m-%d"),
                                  "Transactions": list(range(20)), "Units_Sold": list(range(20)),
                                  "Estimated Revenue": [value * 2.35 for value in range(20)]})
    view.show_result(result)
    assert view.chart_view.mode == "line"
    assert view.chart_view.area is not None
    assert list(view.chart_view.line.get_ydata()) == list(result.periods["Estimated Revenue"])
    vertices = view.chart_view.area.get_paths()[0].vertices
    assert min(vertices[:, 1]) == 0
    view.chart_metric.setCurrentIndex(view.chart_metric.findData("Units_Sold"))
    assert len(view.chart_view.axes.lines) == 1
    assert len(view.chart_view.axes.collections) == 1
    assert view.chart_view.line.get_ydata()[-1] == 19
    assert max(view.chart_view.area.get_paths()[0].vertices[:, 1]) == 19
    frame = pd.DataFrame({"Product_Category": ["A", "B", "C"], "Transactions": [100, 2, 10],
                          "Units_Sold": [100, 2, 10], "Estimated Revenue": [235.0, 4.7, 23.5]})
    view.models["categories"].set_frame(frame)
    table = view.table_views["categories"]
    table.sortByColumn(1, Qt.AscendingOrder)
    assert [table.model().index(row, 1).data() for row in range(3)] == ["2", "10", "100"]
    assert table.model().index(0, 3).data() == "$4.70"
    assert table.model().index(0, 3).data(Qt.TextAlignmentRole) & Qt.AlignRight
    window.close()


def test_custom_dates_and_import_disclosure(app, sample_project):
    window = MainWindow((sample_project,))
    view = window.reports
    assert view.custom_dates.isHidden()
    view.preset.setCurrentText("Özel tarih aralığı")
    assert not view.custom_dates.isHidden()
    assert view.start_date.isEnabled() and view.end_date.isEnabled()
    view.preset.setCurrentText("Tüm zamanlar")
    assert view.custom_dates.isHidden()
    assert view.current_filters().start is None
    window.file_edit.setText(str(sample_project.root / "sales.csv"))
    assert window.selected_file.text() == "sales.csv"
    assert window.log.isHidden()
    window.log_toggle.setChecked(True)
    assert not window.log.isHidden()
    window.step_flow.update_steps(1, running=True)
    assert [step.property("state") for step in window.step_flow.steps] == ["done", "active", "pending"]
    window.step_flow.update_steps(1, failed=True)
    assert window.step_flow.steps[1].property("state") == "error"
    window.close()
