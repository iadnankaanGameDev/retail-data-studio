from pathlib import Path
import pytest
from test_desktop import app
from desktop import MainWindow
import runtime


def test_empty_first_launch_can_create_project(app, tmp_path):
    window = MainWindow(projects=[], project_store=tmp_path / "projects")
    assert window.project is None
    assert window.pages.currentIndex() == 2
    assert window.project_manager.create_button.isEnabled()
    assert not window.start_button.isEnabled()
    assert not window.reports.isEnabled()
    window.choose_file()
    window.start_processing()
    assert window.process is None
    window.close()


def test_frozen_worker_uses_sibling_executable(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "FROZEN", True)
    monkeypatch.setattr(runtime.sys, "executable", str(tmp_path / "RetailDataStudio.exe"))
    assert runtime.worker_command(Path("irrelevant/src/main.py")) == [
        str(tmp_path / "RetailDataWorker.exe"), "--stage", "main"]


def test_data_override_is_explicit_and_absolute(monkeypatch, tmp_path):
    monkeypatch.setenv("RDS_DATA_HOME", str(tmp_path))
    assert runtime.user_data_root() == tmp_path
    monkeypatch.setenv("RDS_DATA_HOME", "relative")
    with pytest.raises(ValueError):
        runtime.user_data_root()
