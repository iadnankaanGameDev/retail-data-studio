"""Windows extended paths at filesystem boundaries, without changing stored paths."""
import os
from pathlib import Path
from urllib.parse import quote


def fs_path(value):
    """Absolute I/O path; bypass MAX_PATH without requiring machine policy changes."""
    path = os.path.abspath(os.fspath(value))
    if os.name == "nt" and not path.startswith("\\\\?\\"):
        path = "\\\\?\\UNC\\" + path[2:] if path.startswith("\\\\") else "\\\\?\\" + path
    return Path(path)


def display_path(value):
    """Keep project identities and UI paths in ordinary Windows notation."""
    path = os.fspath(value)
    if os.name == "nt":
        if path.startswith("\\\\?\\UNC\\"):
            path = "\\\\" + path[8:]
        elif path.startswith("\\\\?\\"):
            path = path[4:]
    return Path(path)


def readonly_uri(value):
    path = fs_path(value)
    if os.name == "nt":
        # Empty URI authority; encode '?' in the extended-path prefix as data.
        return "file://" + quote(str(path).replace("\\", "/"), safe="/:") + "?mode=ro"
    return path.as_uri() + "?mode=ro"
