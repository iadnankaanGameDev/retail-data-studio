"""Backup acceptance and hostile archive tests; all writes stay under tmp_path."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import zipfile

import pytest

from test_project_manager import catalogs, ROOT
from filesystem import fs_path
from project_manager import create_project, load_projects
from project_backup import backup_project, restore_project, FILES
from reporting import query_report, ReportFilter, export_report


def tree_bytes(root):
    return {str(p.relative_to(fs_path(root))): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in fs_path(root).rglob("*") if p.is_file()}


def pipeline(project, source, run):
    output = project.output_root / run
    result = subprocess.run([sys.executable, str(ROOT / "src/main.py"), source.name,
        "--incoming-dir", str(source.parent), "--reference-dir", str(project.reference_dir),
        "--db-path", str(project.database), "--output-dir", str(output),
        "--quarantine-dir", str(project.quarantine_dir / run), "--log-dir", str(output / "logs")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    assert fs_path(output / "store_daily_summary.csv").is_file()
    return json.loads(fs_path(output / "sales_load_summary.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("long_path", [False, True])
def test_roundtrip_etl_catalogs_reports_and_no_overwrites(tmp_path, catalogs, long_path):
    base = tmp_path
    if long_path:
        while len(str(base)) < 290:
            base /= "Türkçe uzun klasör 0123456789"
    fs_path(base).mkdir(parents=True, exist_ok=True)
    project = create_project("Original", *catalogs, base / "installation-a")
    other = create_project("Other", *catalogs, base / "installation-b")
    source = base / "sales.csv"
    fs_path(source).write_text("Sale_ID,Date,Store_ID,Product_ID,Units\n"
        "1,2024-01-01,8001,9001,1\n2,2024-01-02,8001,9001,2\n3,2024-01-03,8001,9001,3\n", encoding="utf-8")
    assert pipeline(project, source, "first")["new_records"] == 3
    before, other_before = tree_bytes(project.root), tree_bytes(other.root)
    archive = base / "yedek.rdsbackup"
    backup_project(project, archive)
    restored = restore_project(archive, "Restored", base / "installation-b")
    assert restored.key not in (project.key, other.key)
    assert query_report(restored, ReportFilter()).totals == query_report(project, ReportFilter()).totals == {
        "Transactions": 3, "Units_Sold": 6, "Estimated Revenue": 75.0}
    for catalog in ("products.csv", "stores.csv"):
        assert fs_path(restored.reference_dir / catalog).read_bytes() == fs_path(project.reference_dir / catalog).read_bytes()
    assert fs_path(export_report(query_report(restored, ReportFilter()), restored.output_root) / "totals.csv").is_file()
    assert pipeline(restored, source, "again")["new_records"] == 0
    assert tree_bytes(project.root) == before
    assert tree_bytes(other.root) == other_before
    assert len(load_projects(base / "installation-b")[0]) == 2
    with pytest.raises(ValueError, match="zaten var"):
        restore_project(archive, "other", base / "installation-b")
    archive_before = fs_path(archive).read_bytes()
    with pytest.raises(ValueError, match="zaten var"):
        backup_project(project, archive)
    assert fs_path(archive).read_bytes() == archive_before


@pytest.fixture
def backup(tmp_path, catalogs):
    project = create_project("Original", *catalogs, tmp_path / "source")
    archive = tmp_path / "valid.rdsbackup"
    backup_project(project, archive)
    return project, archive


@pytest.mark.parametrize("attack", ["tamper", "traversal", "absolute", "backslash", "symlink", "duplicate",
    "unexpected", "missing", "version", "config_path", "database", "trigger", "truncated", "oversize"])
def test_reject_bad_archives_without_partial_project(tmp_path, backup, attack):
    project, archive = backup
    before = tree_bytes(project.root)
    with zipfile.ZipFile(archive) as z:
        items = {n: z.read(n) for n in z.namelist()}
    if attack == "tamper":
        items[FILES[2]] += b"tampered"
    elif attack in ("traversal", "absolute", "backslash", "unexpected"):
        items[{"traversal": "../escape", "absolute": "C:/escape", "backslash": "..\\escape", "unexpected": "extra.txt"}[attack]] = b"bad"
    elif attack == "missing":
        del items[FILES[2]]
    elif attack in ("version", "oversize"):
        manifest = json.loads(items["manifest.json"])
        if attack == "version":
            manifest["format_version"] = 999
        else:
            manifest["files"][FILES[2]]["size"] = 2**40
        items["manifest.json"] = json.dumps(manifest).encode()
    elif attack in ("config_path", "database", "trigger"):
        relative = "project.json" if attack == "config_path" else FILES[1]
        if attack == "config_path":
            config = json.loads(items[relative])
            config["paths"]["database"] = "../sales.db"
            items[relative] = json.dumps(config).encode()
        elif attack == "database":
            items[relative] = b"not sqlite"
        else:
            dbpath = tmp_path / "hostile.db"
            dbpath.write_bytes(items[relative])
            with closing(sqlite3.connect(dbpath)) as db:
                db.execute("CREATE TRIGGER bad AFTER INSERT ON sales BEGIN DELETE FROM sales; END")
                db.commit()
            items[relative] = dbpath.read_bytes()
        manifest = json.loads(items["manifest.json"])
        manifest["files"][relative] = {"size": len(items[relative]), "sha256": hashlib.sha256(items[relative]).hexdigest()}
        items["manifest.json"] = json.dumps(manifest).encode()
    broken = tmp_path / "broken.rdsbackup"
    with zipfile.ZipFile(broken, "w") as z:
        for name, content in items.items():
            info = zipfile.ZipInfo(name)
            if attack == "symlink" and name == FILES[2]:
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, content)
        if attack == "duplicate":
            with pytest.warns(UserWarning):
                z.writestr(FILES[2], items[FILES[2]])
    if attack == "truncated":
        broken.write_bytes(broken.read_bytes()[:80])
    store = tmp_path / "target"
    with pytest.raises((ValueError, zipfile.BadZipFile, sqlite3.DatabaseError)):
        restore_project(broken, "Rejected", store)
    assert list(store.iterdir()) == []
    assert tree_bytes(project.root) == before
    assert not (tmp_path / "escape").exists()


def test_snapshot_includes_wal_and_failure_cleanup(tmp_path, backup, monkeypatch):
    project, _ = backup
    with closing(sqlite3.connect(project.database)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("INSERT INTO sales VALUES (1, '2024-01-01', 8001, 9001, 2)")
        db.commit()
        archive = tmp_path / "wal.rdsbackup"
        backup_project(project, archive)
        restored = restore_project(archive, "WAL", tmp_path / "target")
        assert query_report(restored, ReportFilter()).totals["Units_Sold"] == 2
    import project_backup
    def fail(*args):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(project_backup, "_check_database", fail)
    with pytest.raises(OSError):
        restore_project(archive, "Failure", tmp_path / "failed")
    assert list((tmp_path / "failed").iterdir()) == []
    with pytest.raises(OSError):
        backup_project(project, tmp_path / "failed.rdsbackup")
    assert not (tmp_path / "failed.rdsbackup").exists()
    assert not list(tmp_path.glob(".rds-backup-*"))


def test_restore_publish_failure_cleans_only_own_staging(tmp_path, backup, monkeypatch):
    project, archive = backup
    before = tree_bytes(project.root)
    def fail(*args):
        raise OSError("simulated publication failure")
    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises(OSError, match="publication"):
        restore_project(archive, "New", tmp_path / "source")
    assert [p.name for p in (tmp_path / "source").iterdir()] == [project.key]
    assert tree_bytes(project.root) == before


@pytest.mark.skipif(os.name != "nt", reason="Windows exclusive rename semantics")
def test_backup_destination_race_never_overwrites(tmp_path, backup, monkeypatch):
    project, _ = backup
    destination = tmp_path / "race.rdsbackup"
    original_rename = Path.rename
    def race(source, target):
        fs_path(target).write_bytes(b"other user's file")
        return original_rename(source, target)
    monkeypatch.setattr(Path, "rename", race)
    with pytest.raises(FileExistsError):
        backup_project(project, destination)
    assert destination.read_bytes() == b"other user's file"
    assert not list(tmp_path.glob(".rds-backup-*"))
