"""Application resources, persistent user data and frozen worker dispatch."""
import os
from pathlib import Path
import sys

FROZEN = bool(getattr(sys, "frozen", False))
APP_VERSION = "2.5"
_instance_mutex = None


def hold_instance_mutex():
    """Let the installer detect running GUI/worker processes without killing them."""
    global _instance_mutex
    if FROZEN and os.name == "nt" and _instance_mutex is None:
        import ctypes
        from ctypes import wintypes
        create = ctypes.windll.kernel32.CreateMutexW
        create.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
        create.restype = wintypes.HANDLE
        _instance_mutex = create(None, False, "Local\\RetailDataStudio.Running")
        if not _instance_mutex:
            raise OSError("Unable to register application lifecycle mutex")


def user_data_root():
    override = os.environ.get("RDS_DATA_HOME")
    if override:
        path = Path(override)
        if not path.is_absolute():
            raise ValueError("RDS_DATA_HOME must be an absolute path")
        return path
    from PySide6.QtCore import QCoreApplication, QStandardPaths
    QCoreApplication.setOrganizationName("RetailDataStudio")
    QCoreApplication.setApplicationName("RetailDataStudio")
    return Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))


def worker_command(script):
    if FROZEN:
        return [str(Path(sys.executable).parent / "RetailDataWorker.exe"), "--stage", Path(script).stem]
    return [sys.executable, str(script)]
