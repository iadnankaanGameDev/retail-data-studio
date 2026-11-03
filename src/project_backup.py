"""Portable, allowlisted project archives. Never extract user-provided paths."""
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import time
from uuid import uuid4
import zipfile

from filesystem import fs_path, display_path, readonly_uri
from paths import BASE_DIR
from runtime import APP_VERSION
from project_manager import DEFAULT_STORE, PATHS, TEMPLATE, load_projects, read_project, validate_catalogs

FORMAT = "retail-data-studio-project"
VERSION = 1
FILES = ("project.json", PATHS["database"], "data/raw/products.csv", "data/raw/stores.csv")
MAX_TOTAL = 8 * 1024**3
MAX_JSON = 64 * 1024


def _json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("JSON içinde tekrarlanan alan var.")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)


def _config(config):
    if not isinstance(config, dict) or config.get("schema_version") != 1 or config.get("template") != TEMPLATE:
        raise ValueError("Desteklenmeyen proje sürümü veya şablonu.")
    if config.get("paths") != PATHS or not re.fullmatch(r"[0-9a-f]{32}", str(config.get("id", ""))):
        raise ValueError("Geçersiz proje kimliği veya dosya yolları.")
    _name(config.get("name"))
    return config


def _name(name):
    if not isinstance(name, str) or not name.strip() or len(name) > 100 or any(ord(c) < 32 for c in name):
        raise ValueError("Proje adı 1–100 görünür karakter içermelidir.")
    return name.strip()


def _digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _check_database(path):
    with closing(sqlite3.connect(readonly_uri(path), uri=True)) as db:
        db.execute("PRAGMA trusted_schema=OFF")
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite bütünlük kontrolü başarısız.")
        # Reject executable schema objects and foreign schemas before the ETL opens this database.
        objects = db.execute("SELECT type, name FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%'").fetchall()
        if objects != [("table", "sales")]:
            raise ValueError("Desteklenmeyen veritabanı şeması.")
        columns = db.execute("PRAGMA table_info(sales)").fetchall()
        if [(c[1], c[2].upper(), c[5]) for c in columns] != [
            ("Sale_ID", "INTEGER", 1), ("Date", "TEXT", 0), ("Store_ID", "INTEGER", 0),
            ("Product_ID", "INTEGER", 0), ("Units", "INTEGER", 0)]:
            raise ValueError("Satış tablosu şeması uyumsuz.")


def backup_project(project, destination):
    """Create a new archive exclusively; source DB is opened read-only and snapshotted."""
    destination = fs_path(destination)
    root = fs_path(project.root).resolve()
    if destination.resolve().is_relative_to(root):
        raise ValueError("Yedeği proje klasörünün dışında kaydedin.")
    if destination.exists():
        raise ValueError("Hedef dosya zaten var. Farklı bir dosya adı seçin.")
    if not project.managed:
        raise ValueError("Yalnızca Projects ekranında oluşturulan projeler yedeklenebilir.")
    read_project(root)
    for relative in FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Proje dosyası eksik veya güvenli değil: {relative}")
    config = _config(_json((root / "project.json").read_bytes()))
    with tempfile.TemporaryDirectory(prefix=".rds-backup-", dir=destination.parent) as temp:
        stage = fs_path(temp)
        for relative in FILES:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if relative == PATHS["database"]:
                deadline = time.monotonic() + 120
                def progress(*_):
                    if time.monotonic() > deadline:
                        raise TimeoutError("Veritabanı snapshot işlemi zaman aşımına uğradı. Tekrar deneyin.")
                with closing(sqlite3.connect(readonly_uri(project.database), uri=True)) as source:
                    with closing(sqlite3.connect(target)) as snapshot:
                        source.backup(snapshot, pages=256, progress=progress)
            else:
                shutil.copyfile(root / relative, target)
        _check_database(stage / PATHS["database"])
        validate_catalogs(stage / FILES[2], stage / FILES[3])
        manifest = {"format": FORMAT, "format_version": VERSION, "application_version": APP_VERSION,
                    "created_at": datetime.now(timezone.utc).isoformat(), "source_project_id": config["id"],
                    "files": {p: {"size": (stage / p).stat().st_size, "sha256": _digest(stage / p)} for p in FILES}}
        if sum(item["size"] for item in manifest["files"].values()) > MAX_TOTAL:
            raise ValueError("Proje 8 GiB yedek sınırını aşıyor.")
        archive = stage / "archive.rdsbackup"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
            for relative in FILES:
                bundle.write(stage / relative, relative)
        # Exclusive publication on Windows; no existing destination is replaced.
        if os.name == "nt":
            archive.rename(destination)
        else:
            os.link(archive, destination)
    return display_path(destination)


def restore_project(archive, name, store=DEFAULT_STORE, pipeline_root=BASE_DIR):
    """Validate structure and every hash in private staging, then publish a fresh ID."""
    name = _name(name)
    store = fs_path(store).resolve()
    existing, _ = load_projects(store, pipeline_root)
    if any(p.name.casefold() == name.casefold() for p in existing):
        raise ValueError("Bu proje adı zaten var. Yeni bir ad seçin.")
    store.mkdir(parents=True, exist_ok=True)
    key = uuid4().hex
    # TemporaryDirectory only removes the private directory created by this call.
    with tempfile.TemporaryDirectory(prefix=".restoring-", dir=store) as temp:
        staging = fs_path(temp) / key
        staging.mkdir()
        with zipfile.ZipFile(fs_path(archive), "r") as bundle:
            entries = bundle.infolist()
            allowed = set(FILES) | {"manifest.json"}
            if len(entries) != len(allowed) or {i.filename for i in entries} != allowed:
                raise ValueError("Yedek dosya yapısı geçersiz: eksik, tekrarlı veya beklenmeyen dosya.")
            for entry in entries:
                mode = entry.external_attr >> 16
                if (entry.orig_filename != entry.filename or entry.is_dir() or
                        stat.S_IFMT(mode) not in (0, stat.S_IFREG) or entry.external_attr & 0x410 or
                        entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                    raise ValueError("Yedek bağlantı, özel dosya veya desteklenmeyen sıkıştırma içeriyor.")
            if sum(i.file_size for i in entries) > MAX_TOTAL or bundle.getinfo("manifest.json").file_size > MAX_JSON:
                raise ValueError("Yedek boyut sınırını aşıyor.")
            manifest = _json(bundle.read("manifest.json"))
            if (not isinstance(manifest, dict) or manifest.get("format") != FORMAT or
                    manifest.get("format_version") != VERSION or not isinstance(manifest.get("files"), dict) or
                    set(manifest["files"]) != set(FILES)):
                raise ValueError("Desteklenmeyen veya geçersiz yedek manifesti.")
            for relative in FILES:
                metadata = manifest["files"][relative]
                entry = bundle.getinfo(relative)
                if (not isinstance(metadata, dict) or type(metadata.get("size")) is not int or
                        metadata["size"] != entry.file_size or
                        not re.fullmatch(r"[0-9a-f]{64}", str(metadata.get("sha256", "")))):
                    raise ValueError("Manifest dosya boyutu veya SHA-256 alanı geçersiz.")
                if relative == "project.json" and entry.file_size > MAX_JSON:
                    raise ValueError("Proje yapılandırması çok büyük.")
                target = staging / relative  # constant allowlist, never an archive-supplied path
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                count = 0
                with bundle.open(relative) as source, target.open("xb") as output:
                    while chunk := source.read(1024 * 1024):
                        count += len(chunk)
                        if count > metadata["size"]:
                            raise ValueError("Açılan dosya boyut sınırını aşıyor.")
                        digest.update(chunk)
                        output.write(chunk)
                if count != metadata["size"] or digest.hexdigest() != metadata["sha256"]:
                    raise ValueError(f"SHA-256 bütünlük kontrolü başarısız: {relative}")
        config = _config(_json((staging / "project.json").read_bytes()))
        if manifest.get("source_project_id") != config["id"]:
            raise ValueError("Manifest proje kimliği eşleşmiyor.")
        validate_catalogs(staging / FILES[2], staging / FILES[3])
        _check_database(staging / PATHS["database"])
        config.update(id=key, name=name, restored_from=config["id"],
                      restored_at=datetime.now(timezone.utc).isoformat())
        (staging / "project.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        for relative in PATHS.values():
            target = staging / relative
            (target.parent if target.suffix == ".db" else target).mkdir(parents=True, exist_ok=True)
        final = store / key
        project = read_project(staging, pipeline_root)
        # Build result before publishing, so no fallible reads occur after publication.
        result = replace(project, root=display_path(final))
        if final.exists():
            raise ValueError("Yeni proje kimliği çakıştı. Tekrar deneyin.")
        staging.rename(final)
    return result
