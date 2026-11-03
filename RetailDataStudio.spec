# Build with: .venv\Scripts\python.exe -m PyInstaller RetailDataStudio.spec
from pathlib import Path
import os
import sys
root = Path(SPECPATH)
# Do not let unrelated developer tools (Poppler/Conda/etc.) supply DLLs by name.
os.environ['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
a = Analysis(
    [str(root / 'src/desktop.py'), str(root / 'src/worker_entry.py'), str(root / 'scripts/delivery_probe.py'), str(root / 'scripts/backup_delivery_probe.py')],
    pathex=[str(root / 'src'), str(root / 'scripts')],
    datas=[(str(root / 'src/assets/chevron-down.svg'), 'assets'), (str(root / 'src/assets/retail.ico'), 'assets')],
    hiddenimports=['main', 'process_incoming', 'load_sales', 'generate_reports'],
    excludes=['pytest', 'tkinter', 'IPython', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6.QtCharts', 'PySide6.QtVirtualKeyboard', 'PySide6.QtQuick', 'PySide6.QtPdf', 'PySide6.QtWebEngineCore', 'PySide6.QtQml'],
    hooksconfig={"matplotlib": {"backends": ["QtAgg"]}},
    noarchive=False,
)
allowed = [root, Path(sys.base_prefix), Path(os.environ['SystemRoot'])]
for destination, source, kind in a.binaries:
    if not any(Path(source).resolve().is_relative_to(folder.resolve()) for folder in allowed):
        raise RuntimeError(f'Unexpected external binary dependency: {source}')
# Prune native plugins too: Python excludes alone do not remove their DLLs.
sys.path.insert(0, str(root / 'scripts'))
from package_policy import allowed_binary, validate_native_dependencies
a.binaries = [item for item in a.binaries if allowed_binary(item[0])]
a.datas = [item for item in a.datas if allowed_binary(item[0])
           and "matplotlib/mpl-data/sample_data/" not in item[0].replace("\\", "/")]
validate_native_dependencies(a.binaries)
pyz = PYZ(a.pure)
def entry(name):
    return [item for item in a.scripts if item[0] not in {'desktop', 'worker_entry', 'delivery_probe', 'backup_delivery_probe'} or item[0] == name]
gui = EXE(pyz, entry('desktop'), [], exclude_binaries=True, name='RetailDataStudio', console=False, upx=False, icon=str(root / 'src/assets/retail.ico'), version=str(root / 'installer/version_info.txt'))
worker = EXE(pyz, entry('worker_entry'), [], exclude_binaries=True, name='RetailDataWorker', console=True, upx=False, version=str(root / 'installer/version_info.txt'))
# QA harness is deliberately outside the customer folder; never include in ZIP.
probe = EXE(pyz, entry('delivery_probe'), [], exclude_binaries=True, name='DeliveryProbe', console=True, upx=False)
backup_probe = EXE(pyz, entry('backup_delivery_probe'), [], exclude_binaries=True, name='BackupDeliveryProbe', console=True, upx=False)
coll = COLLECT(gui, worker, a.binaries, a.datas, name='RetailDataStudio', upx=False)
