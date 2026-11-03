"""Versioned, isolated Sales ETL projects. No production data is copied."""
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
from uuid import uuid4

import pandas as pd

from init_db import initialize_database
from paths import BASE_DIR
from projects import Project
from reporting import price_cents
from filesystem import fs_path, display_path

DEFAULT_STORE = BASE_DIR / "data/projects"
TEMPLATE = "sales_etl_v1"
PATHS = {"database": "data/database/sales.db", "references": "data/raw",
         "incoming": "data/incoming", "processed": "data/processed",
         "quarantine": "data/quarantine"}


def validate_catalogs(products_path, stores_path):
    products = pd.read_csv(fs_path(products_path), dtype={"Product_Price": "string", "Product_Cost": "string"})
    stores = pd.read_csv(fs_path(stores_path))
    for frame, required, identifier in (
        (products, ["Product_ID", "Product_Category", "Product_Price", "Product_Cost"], "Product_ID"),
        (stores, ["Store_ID", "Store_Name"], "Store_ID"),
    ):
        missing = set(required) - set(frame.columns)
        if missing:
            raise ValueError(f"Eksik katalog kolonları: {', '.join(sorted(missing))}")
        if frame.empty or frame[required].isna().any().any():
            raise ValueError("Katalog boş olamaz; gerekli alanlar eksiksiz olmalıdır.")
        ids = pd.to_numeric(frame[identifier], errors="coerce")
        if ids.isna().any() or (ids <= 0).any() or (ids % 1 != 0).any() or ids.duplicated().any():
            raise ValueError(f"{identifier}: benzersiz, pozitif tam sayılar gereklidir.")
        frame[identifier] = ids.astype("int64")
    for frame, column in ((products, "Product_Category"), (stores, "Store_Name")):
        frame[column] = frame[column].astype("string").str.strip()
        if frame[column].eq("").any():
            raise ValueError(f"{column} boş olamaz.")
    for column in ("Product_Price", "Product_Cost"):
        cents = products[column].map(price_cents)
        # The existing report script expects currency strings; normalize only the new local copy.
        products[column] = cents.map(lambda value: f"${value // 100}.{value % 100:02d}")
    return products, stores


def read_project(folder, pipeline_root=BASE_DIR):
    folder = fs_path(folder)
    config = json.loads((folder / "project.json").read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Proje yapılandırması bir JSON nesnesi olmalıdır")
    if config.get("schema_version") != 1 or config.get("template") != TEMPLATE:
        raise ValueError("Desteklenmeyen proje sürümü veya şablonu")
    key = config.get("id", "")
    if not re.fullmatch(r"[0-9a-f]{32}", key) or folder.name != key:
        raise ValueError("Proje kimliği klasörle eşleşmiyor")
    name = config.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise ValueError("Geçersiz proje adı")
    # This template intentionally has fixed relative paths, not arbitrary external paths.
    if config.get("paths") != PATHS:
        raise ValueError("Sales ETL Template yolları değiştirilmiş veya geçersiz")
    for path in PATHS.values():
        if not (folder / path).resolve().is_relative_to(folder.resolve()):
            raise ValueError("Proje yolu çalışma alanının dışına çıkamaz")
    for name_in_catalog in ("products.csv", "stores.csv"):
        if not (folder / PATHS["references"] / name_in_catalog).resolve().is_relative_to(folder.resolve()):
            raise ValueError("Referans dosyası başka bir projeye yönlendirilemez")
    return Project(key, name.strip(), display_path(folder.resolve()), "Sales ETL Template",
                   PATHS["database"], PATHS["processed"], Path(pipeline_root), True, TEMPLATE)


def load_projects(store=DEFAULT_STORE, pipeline_root=BASE_DIR):
    """Return valid registrations and visible diagnostics; never repair/create databases."""
    store = fs_path(store)
    projects, errors = [], []
    if not store.exists():
        return projects, errors
    try:
        folders = sorted(store.iterdir())
    except OSError as exc:
        return [], [f"Proje listesi okunamadı: {exc}"]
    for folder in folders:
        if folder.name.startswith(".") or not folder.is_dir():
            continue
        try:
            if folder.resolve().parent != store.resolve() or folder.is_symlink():
                raise ValueError("Proje klasörü dışarı yönlendirilemez")
            projects.append(read_project(folder, pipeline_root))
        except (ValueError, OSError, TypeError) as exc:
            errors.append(f"{folder.name}: {exc}")
    return projects, errors


def create_project(name, products_path, stores_path, store=DEFAULT_STORE, pipeline_root=BASE_DIR):
    name = name.strip()
    if not name or len(name) > 100 or any(ord(char) < 32 for char in name):
        raise ValueError("Proje adı 1–100 görünür karakter içermelidir.")
    products, stores = validate_catalogs(products_path, stores_path)
    store = fs_path(store).resolve()
    store.mkdir(parents=True, exist_ok=True)
    key = uuid4().hex
    staging = store / f".creating-{key}"
    final = store / key
    staging.mkdir()  # exclusive, generated directory; never reuses an existing workspace
    try:
        for relative in PATHS.values():
            target = staging / relative
            (target.parent if target.suffix == ".db" else target).mkdir(parents=True, exist_ok=True)
        products.to_csv(staging / PATHS["references"] / "products.csv", index=False, encoding="utf-8-sig")
        stores.to_csv(staging / PATHS["references"] / "stores.csv", index=False, encoding="utf-8-sig")
        initialize_database(staging / PATHS["database"])
        config = {"schema_version": 1, "id": key, "name": name, "template": TEMPLATE,
                  "created_at": datetime.now().astimezone().isoformat(), "paths": PATHS}
        (staging / "project.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        staging.rename(final)  # publishes only a complete project; Windows refuses an existing target
    except BaseException:
        # Delete only this call's private staging directory, never user-selected sources.
        if staging.exists() and staging.resolve().parent == store and staging.name == f".creating-{key}":
            shutil.rmtree(staging)
        raise
    return read_project(final, pipeline_root)
