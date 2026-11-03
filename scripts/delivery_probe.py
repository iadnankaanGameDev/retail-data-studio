"""Build-only frozen integration probe. Not included in the customer folder."""
import json
import os
from pathlib import Path
import sys
import time

from PySide6.QtWidgets import QApplication
from desktop import MainWindow, STYLE
from runtime import user_data_root, FROZEN
from reporting import query_report, ReportFilter, export_report
from filesystem import fs_path


def wait(app, predicate, seconds=60):
    deadline = time.monotonic() + seconds
    while predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    if predicate():
        raise RuntimeError("Delivery probe timed out")
    app.processEvents()


def verify_charts(app, window, root):
    from matplotlib.backend_bases import MouseEvent
    from PySide6.QtWidgets import QToolTip
    from datetime import date
    results = []
    view = window.reports
    for grouping in ("Günlük", "Haftalık", "Aylık"):
        view.grouping.setCurrentText(grouping)
        view.load_report()
        wait(app, lambda: view.busy)
        assert view.result is not None
        assert view.result.totals == {"Transactions": 3, "Units_Sold": 6, "Estimated Revenue": 75.0}
        for metric in ("Estimated Revenue", "Units_Sold", "Transactions"):
            view.chart_metric.setCurrentIndex(view.chart_metric.findData(metric))
            app.processEvents()
            chart = view.chart_view
            chart.draw()
            assert chart.rows and chart.isVisible() and not view.empty_state.isVisible()
            assert sum(float(r[metric]) for r in chart.rows) == view.result.totals[metric]
            x, y = chart.axes.transData.transform((chart.x[0], float(chart.rows[0][metric]) / 2))
            event = MouseEvent("motion_notify_event", chart, x, y)
            chart.callbacks.process("motion_notify_event", event)
            assert chart._hover_index == 0
            assert QToolTip.text() == chart.tooltip_text(0)
            chart._leave()
            assert chart._hover_index is None
            results.append({"grouping": grouping, "metric": metric, "periods": len(chart.rows), "hover": True})
        window.grab().save(str(root / (grouping + ".png")))
    empty = query_report(window.project, ReportFilter(start=date(2000,1,1), end=date(2000,1,2)))
    view.show_result(empty)
    app.processEvents()
    assert view.empty_state.isVisible() and not view.chart_view.isVisible()
    assert view.chart_view.mode == "empty" and not view.chart_view.rows
    view.load_report()
    wait(app, lambda: view.busy)
    return {"cases": results, "empty_state": True, "backend": type(view.chart_view).__name__}


def main():
    assert FROZEN
    # QA always needs an explicitly isolated absolute root, never customer defaults.
    assert os.environ.get("RDS_DATA_HOME")
    root = fs_path(user_data_root())
    root.mkdir(parents=True, exist_ok=True)
    phase = sys.argv[1]
    app = QApplication([])
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    app.processEvents()
    if phase == "create":
        assert not window.projects and window.pages.currentIndex() == 2
        assert not window.start_button.isEnabled()
        products, stores = root / "products.csv", root / "stores.csv"
        products.write_text("Product_ID,Product_Category,Product_Price,Product_Cost\n9001,Toys,$12.50,$5.00\n", encoding="utf-8")
        stores.write_text("Store_ID,Store_Name\n8001,Delivery Store\n", encoding="utf-8")
        view = window.project_manager
        view.name_edit.setText("Portable verification")
        view.products_edit.setText(str(products))
        view.stores_edit.setText(str(stores))
        view.start_create()
        wait(app, lambda: view.busy)
        assert window.project is not None, view.status.text()
        source = window.project.incoming_dir / "three_sales.csv"
        fs_path(source).write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n1,2026-10-20,8001,9001,1\n2,2026-10-21,8001,9001,2\n3,2026-10-22,8001,9001,3\n", encoding="utf-8")
        counts = []
        for expected in (3, 0):
            window.file_edit.setText(str(source))
            window.start_processing()
            wait(app, lambda: window.process is not None)
            assert "Tamamlandı" in window.status_label.text(), window.log.toPlainText()
            assert int(window.metrics["new_records"].text()) == expected
            counts.append(expected)
        assert window.metrics["already_present"].text() == "3"
    else:
        assert phase == "reopen" and len(window.projects) == 1
        counts = None
    result = query_report(window.project, ReportFilter())
    assert result.totals == {"Transactions": 3, "Units_Sold": 6, "Estimated Revenue": 75.0}, result.totals
    window.nav_items[1].click()
    window.reports.load_report()
    wait(app, lambda: window.reports.busy)
    assert window.reports.result is not None, window.reports.status.text()
    chart_evidence = verify_charts(app, window, root)
    window.reports.export_current()
    wait(app, lambda: window.reports.busy)
    assert list(fs_path(window.reports.export_folder).glob("*.csv"))
    window.grab().save(str(root / f"{phase}.png"))
    evidence = {"phase": phase, "frozen": FROZEN, "executable": sys.executable,
        "data_root": str(root), "database": str(window.project.database), "totals": result.totals,
        "new_records_each_import": counts, "export": str(window.reports.export_folder),
        "sys_path": sys.path, "charts": chart_evidence}
    (root / f"{phase}.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    window.close()
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
