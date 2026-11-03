import threading
import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from test_desktop import app
from test_project_backup import backup
from test_project_manager import catalogs
from desktop import MainWindow
import projects_view


def wait_task(app, view):
    deadline = time.monotonic() + 20
    while view.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert not view.busy


def test_backup_restore_ui_responsive_and_collision_prompt(app, tmp_path, backup, monkeypatch):
    project, _ = backup
    window = MainWindow((project,), project_store=tmp_path / "source")
    view = window.project_manager
    output = tmp_path / "ui.rdsbackup"
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output), ""))
    release = threading.Event()
    real_backup = projects_view.backup_project
    def slow_backup(*args):
        assert release.wait(10)
        return real_backup(*args)
    monkeypatch.setattr(projects_view, "backup_project", slow_backup)
    view.backup_button.click()
    try:
        assert view.busy
        assert not view.restore_button.isEnabled()
        assert not window.start_button.isEnabled()
        monkeypatch.setattr(QMessageBox, "information", lambda *args: QMessageBox.Ok)
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        ticks = []
        QTimer.singleShot(0, lambda: ticks.append(1))
        app.processEvents()
        assert ticks
    finally:
        release.set()
        wait_task(app, view)
    assert str(output) in view.status.text()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(output), ""))
    answers = iter([(project.name, True), ("Restored UI", True)])
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: next(answers))
    view.restore_button.click()
    wait_task(app, view)
    assert len(window.projects) == 2
    assert window.project.name == "Restored UI"
    assert window.project.key != project.key
    assert view.backup_button.isEnabled()
    window.close()


def test_restore_error_recovers_and_empty_installation_can_restore(app, tmp_path, monkeypatch):
    window = MainWindow(projects=[], project_store=tmp_path / "projects")
    view = window.project_manager
    assert view.restore_button.isEnabled()
    assert not view.backup_button.isEnabled()
    bad = tmp_path / "bad.rdsbackup"
    bad.write_bytes(b"broken")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(bad), ""))
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: ("New", True))
    view.start_restore()
    wait_task(app, view)
    assert "başarısız" in view.status.text()
    assert view.restore_button.isEnabled()
    assert not window.projects
    assert list((tmp_path / "projects").iterdir()) == []
    window.close()
