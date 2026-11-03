from types import SimpleNamespace
from pathlib import Path
import sys
import pandas as pd
import pytest
from test_desktop import app
from report_chart import ReportChart
from matplotlib.backend_bases import MouseEvent
from PySide6.QtWidgets import QToolTip


@pytest.mark.parametrize("grouping", ["Günlük", "Haftalık", "Aylık", "Üç aylık", "Yıllık"])
@pytest.mark.parametrize("count", [0, 1, 18, 19, 365])
def test_period_modes_and_values(app, grouping, count):
    chart = ReportChart()
    frame = pd.DataFrame({"Period": pd.date_range("2024-01-01", periods=count).strftime("%Y-%m-%d"),
                          "Transactions": range(count), "Units_Sold": range(count),
                          "Estimated Revenue": [i * 2.35 for i in range(count)]})
    chart.resize(900, 300)
    for metric in ("Transactions", "Units_Sold", "Estimated Revenue"):
        chart.set_periods(frame, grouping, metric)
        chart.draw()
        assert chart.mode == ("empty" if count == 0 else "bar" if count <= 18 else "line")
        if count:
            values = [bar.get_height() for bar in chart.bars] if chart.mode == "bar" else chart.line.get_ydata()
            assert list(values) == pytest.approx(frame[metric].tolist())
            assert chart.axes.get_ylim()[0] == 0
            assert chart.axes.get_ylim()[1] >= frame[metric].max()
    chart.close()


@pytest.mark.parametrize("count", [3, 30])
def test_hover_metric_change_and_clear(app, monkeypatch, count):
    shown = []
    monkeypatch.setattr(QToolTip, "showText", lambda pos, text, *args: shown.append(text))
    chart = ReportChart()
    frame = pd.DataFrame({"Period": pd.date_range("2024-01-01", periods=count).strftime("%Y-%m-%d"),
                          "Estimated Revenue": [12.50] * count, "Units_Sold": [2] * count})
    chart.resize(900, 300)
    chart.set_periods(frame, "Günlük", "Estimated Revenue")
    chart.draw()
    x, y = chart.axes.transData.transform((chart.x[1], 6))
    chart._hover(MouseEvent("motion_notify_event", chart, x, y))
    assert shown[-1] == "2024-01-02 · Estimated Revenue: $12.50"
    chart.set_periods(frame, "Günlük", "Units_Sold")
    assert chart._hover_index is None
    chart.draw()
    x, y = chart.axes.transData.transform((chart.x[1], 1))
    chart._hover(MouseEvent("motion_notify_event", chart, x, y))
    assert shown[-1] == "2024-01-02 · Units Sold: 2"
    chart._hover(SimpleNamespace(inaxes=None, xdata=None))
    assert chart._hover_index is None
    chart.set_periods(None, "Günlük", "Units_Sold")
    assert not chart.rows and not chart.axes.lines and not chart.axes.patches
    chart.close()


def test_package_policy_rejects_native_plugins():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from package_policy import allowed_binary
    for name in ("Qt6Charts.dll", "QtCharts.pyd", "qtvirtualkeyboardplugin.dll",
                 "Qt6VirtualKeyboard.dll", "Qt6Qml.dll", "Qt6Quick.dll", "qpdf.dll"):
        assert not allowed_binary("PySide6/plugins/" + name)
    for name in ("Qt6Core.dll", "Qt6Svg.dll", "qwindows.dll", "qjpeg.dll"):
        assert allowed_binary(name)
