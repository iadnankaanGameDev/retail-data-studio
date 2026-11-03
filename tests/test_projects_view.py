import time

from test_desktop import app, run_window
from test_project_manager import catalogs
from desktop import MainWindow
from reporting import query_report, ReportFilter


def test_create_through_ui_import_and_reopen(app, tmp_path, catalogs):
    store = tmp_path / "projects"
    window = MainWindow(project_store=store)
    window.nav_items[2].click()
    manager = window.project_manager
    manager.name_edit.setText("Arayüz projesi")
    manager.products_edit.setText(str(catalogs[0]))
    manager.stores_edit.setText(str(catalogs[1]))
    manager.start_create()
    assert not window.project_box.isEnabled()
    deadline = time.monotonic() + 20
    while manager.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert not manager.busy
    assert window.project.name == "Arayüz projesi", manager.status.text()
    project = window.project
    assert project.managed
    source = project.incoming_dir / "test.csv"
    source.write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n"
                      "1,2024-01-01,8001,9001,1\n2,2024-01-02,8001,9001,2\n"
                      "3,2024-01-03,8001,9001,3\n", encoding="utf-8")
    run_window(app, window, source)
    assert "Tamamlandı" in window.status_label.text(), window.log.toPlainText()
    assert window.metrics["new_records"].text() == "3"
    run_window(app, window, source)
    assert window.metrics["new_records"].text() == "0"
    assert window.metrics["already_present"].text() == "3"
    from filesystem import fs_path
    assert fs_path(project.quarantine_dir / window.output_dir.name / "test_rejected.csv").is_file()
    assert query_report(project, ReportFilter()).totals["Estimated Revenue"] == 75
    window.close()
    reopened = MainWindow(project_store=store)
    assert len(reopened.projects) == 3
    reopened.activate_project(project.key)
    assert reopened.project.database == project.database
    assert reopened.reports.project.key == project.key
    reopened.close()
