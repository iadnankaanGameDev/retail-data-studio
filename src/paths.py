
from pathlib import Path
import sys
from filesystem import fs_path

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent
if getattr(sys, "frozen", False):
    from runtime import user_data_root
    BASE_DIR = user_data_root()
SRC_DIR = Path(__file__).resolve().parent

# Data directories
DATA_DIR = BASE_DIR / "data"

RAW_DIR = DATA_DIR / "raw"
INCOMING_DIR = DATA_DIR / "incoming"
PROCESSED_DIR = DATA_DIR / "processed"
QUARANTINE_DIR = DATA_DIR / "quarantine"
DATABASE_DIR = DATA_DIR / "database"
LOGS_DIR = DATA_DIR / "logs"

# Default database
DEFAULT_DB_PATH = DATABASE_DIR / "sales.db"


def resolve_project_path(path):
    """Resolve relative paths from the project root."""
    path = Path(path)

    if path.is_absolute():
        return fs_path(path)

    return fs_path(BASE_DIR / path)
