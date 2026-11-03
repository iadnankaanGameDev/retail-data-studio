"""Frozen V2.4 QA entrypoint, excluded from the customer delivery folder."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import zipfile

from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
from desktop import MainWindow, STYLE
from delivery_probe import wait
from filesystem import fs_path, readonly_uri
from runtime import FROZEN, user_data_root, APP_VERSION
from reporting import query_report, ReportFilter


def fingerprint(root):
    result = {}
    for path in fs_path(root).rglob("*"):
        if path.is_file():
            with path.open("rb") as stream:
                result[path.relative_to(fs_path(root)).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def rows(project):
    with closing(sqlite3.connect(readonly_uri(project.database), uri=True)) as db:
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        return db.execute("SELECT * FROM sales ORDER BY Sale_ID").fetchall()


def main():
    assert FROZEN and os.environ.get("RDS_DATA_HOME")
    root = fs_path(user_data_root())
    root.mkdir(parents=True, exist_ok=True)
    phase = sys.argv[1]
    app = QApplication([])
    app.setStyleSheet(STYLE)
    window = MainWindow()
    assert window.windowTitle().endswith(f"V{APP_VERSION}")
    window.show()
    app.processEvents()
    view = window.project_manager
    evidence = {"phase": phase, "frozen": FROZEN, "executable": sys.executable,
                "sys_path": sys.path, "window_title": window.windowTitle(), "native_dialogs": False}
    archive = root / "synthetic-project.rdsbackup"
    if phase == "create":
        assert not window.projects
        products, stores = root / "products.csv", root / "stores.csv"
        products.write_text("Product_ID,Product_Category,Product_Price,Product_Cost\n9001,Toys,12.50,5.00\n", encoding="utf-8")
        stores.write_text("Store_ID,Store_Name\n8001,Acceptance Store\n", encoding="utf-8")
        view.name_edit.setText("V2.4 Original")
        view.products_edit.setText(str(products))
        view.stores_edit.setText(str(stores))
        view.create_button.click()
        wait(app, lambda: view.busy)
        assert window.project, view.status.text()
        original = window.project
        source = fs_path(original.incoming_dir / "three_sales.csv")
        source.write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n1,2026-10-20,8001,9001,1\n2,2026-10-21,8001,9001,2\n3,2026-10-22,8001,9001,3\n", encoding="utf-8")
        window.file_edit.setText(str(source))
        window.start_processing()
        wait(app, lambda: window.process is not None)
        assert window.metrics["new_records"].text() == "3", window.log.toPlainText()
        before = fingerprint(original.root)
        window.nav_items[2].click()
        # Only user input dialogs are substituted; real handlers, threads and worker EXE run.
        QMessageBox.question = lambda *args: QMessageBox.Yes
        QFileDialog.getSaveFileName = lambda *args: (str(archive), "")
        view.backup_button.click()
        wait(app, lambda: view.busy)
        assert archive.is_file(), view.status.text()
        evidence["backup_status"] = view.status.text()
        with zipfile.ZipFile(archive) as bundle:
            evidence["archive_entries"] = bundle.namelist()
            evidence["manifest"] = json.loads(bundle.read("manifest.json"))
            assert evidence["manifest"]["application_version"] == APP_VERSION
        QFileDialog.getOpenFileName = lambda *args: (str(archive), "")
        QInputDialog.getText = lambda *args: ("V2.4 Restored", True)
        view.restore_button.click()
        wait(app, lambda: view.busy)
        assert len(window.projects) == 2, view.status.text()
        restored = window.project
        assert original.key != restored.key
        assert rows(original) == rows(restored)
        for filename in ("products.csv", "stores.csv"):
            assert fs_path(original.reference_dir / filename).read_bytes() == fs_path(restored.reference_dir / filename).read_bytes()
        window.file_edit.setText(str(source))
        window.start_processing()
        wait(app, lambda: window.process is not None)
        assert window.metrics["new_records"].text() == "0", window.log.toPlainText()
        assert window.metrics["already_present"].text() == "3"
        assert fingerprint(original.root) == before
        evidence.update(new_records=[3, 0], already_present=3, original_unchanged=True,
                        catalogs_equal=True, sales_rows_equal=True, backup=str(archive))
        protected = fingerprint(root / "data/projects")
        bad = root / "tampered.rdsbackup"
        with zipfile.ZipFile(archive) as bundle, zipfile.ZipFile(bad, "w") as output:
            for filename in bundle.namelist():
                content = bundle.read(filename)
                if filename == "data/raw/products.csv":
                    content += b"tampered"
                output.writestr(filename, content)
        QFileDialog.getOpenFileName = lambda *args: (str(bad), "")
        QInputDialog.getText = lambda *args: ("Must not exist", True)
        view.restore_button.click()
        wait(app, lambda: view.busy)
        assert "başarısız" in view.status.text(), view.status.text()
        assert len(window.projects) == 2
        assert fingerprint(root / "data/projects") == protected
        assert not list((root / "data/projects").glob(".restoring-*"))
        evidence.update(corrupt_archive_rejected=True, corruption_error=view.status.text(),
                        no_partial_project=True, projects_unchanged_on_error=True)
    elif phase == "reopen":
        assert len(window.projects) == 2
        evidence["persistence_verified"] = True
    elif phase == "transfer":
        assert not window.projects
        QFileDialog.getOpenFileName = lambda *args: (sys.argv[2], "")
        QInputDialog.getText = lambda *args: ("Other installation", True)
        view.restore_button.click()
        wait(app, lambda: view.busy)
        assert len(window.projects) == 1, view.status.text()
        evidence["fresh_installation_restore"] = True
    else:
        raise ValueError(phase)
    evidence["projects"] = []
    for project in window.projects:
        totals = query_report(project, ReportFilter()).totals
        assert totals == {"Transactions": 3, "Units_Sold": 6, "Estimated Revenue": 75.0}
        assert len(rows(project)) == 3
        evidence["projects"].append({"id": project.key, "name": project.name,
            "database": str(project.database), "totals": totals, "integrity_check": "ok"})
    window.nav_items[1].click()
    window.reports.load_report()
    wait(app, lambda: window.reports.busy)
    assert window.reports.result is not None
    window.reports.export_current()
    wait(app, lambda: window.reports.busy)
    assert list(fs_path(window.reports.export_folder).glob("*.csv"))
    evidence["chart_backend"] = type(window.reports.chart_view).__name__
    evidence["report_export"] = str(window.reports.export_folder)
    window.grab().save(str(root / f"{phase}.png"))
    window.close()
    (root / f"{phase}.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
