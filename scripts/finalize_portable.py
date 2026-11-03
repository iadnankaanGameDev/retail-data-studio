"""Add customer notes, available dependency licenses and a file manifest."""
import hashlib
from importlib.metadata import distribution
import json
from pathlib import Path
import shutil
import sys
import argparse

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--target", type=Path, default=root / "dist/RetailDataStudio")
target = parser.parse_args().target.resolve()
assert (target / "RetailDataStudio.exe").is_file()
shutil.copy2(root / "docs/PORTABLE_QUICKSTART.txt", target / "READ_ME.txt")
shutil.copy2(root / "docs/QUICK_START.md", target / "QUICK_START.md")
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.is_file():
    destination = target / "licenses/Python/LICENSE.txt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(python_license, destination)
for name in ("LGPL-3.0-only.txt", "GPL-3.0-only.txt"):
    destination = target / "licenses/Qt" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "docs/licenses" / name, destination)
shutil.copy2(root / "docs/CHART_MIGRATION_LICENSING.md", target / "LICENSING_STATUS.md")
from package_policy import audit_folder
native_files = audit_folder(target)
(target / "NATIVE_INVENTORY.json").write_text(json.dumps(native_files, indent=2), encoding="utf-8")
versions = {}
for name in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "pandas", "numpy", "python-dateutil", "six", "tzdata", "PyInstaller", "matplotlib", "contourpy", "cycler", "fonttools", "kiwisolver", "Pillow", "pyparsing", "packaging"):
    dist = distribution(name)
    versions[name] = dist.version
    for file in dist.files or []:
        if not any(term in str(file).lower() for term in ("license", "copying", "copyright")):
            continue
        source = Path(dist.locate_file(file))
        if source.is_file() and source.suffix not in (".py", ".pyc", ".dll", ".pyd"):
            destination = target / "licenses" / name / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and destination.read_bytes() != source.read_bytes():
                destination = destination.with_name(hashlib.sha256(str(file).encode()).hexdigest()[:8] + "-" + source.name)
            shutil.copy2(source, destination)
(target / "THIRD_PARTY_NOTICES.txt").write_text(
    "Retail Data Studio includes Python, Qt/PySide6, pandas, NumPy and dependencies.\n"
    "Available package license texts are in licenses/ and _internal/.\n"
    "This inventory is not a complete commercial redistribution clearance.\n"
    "Qt Charts/Virtual Keyboard are excluded by policy. Confirm remaining LGPL source and replacement obligations before shipping.\n\n"
    + "\n".join(f"{key} {value}" for key, value in versions.items()), encoding="utf-8")
files = {}
for path in sorted(target.rglob("*")):
    if not path.is_file() or path.name == "manifest.json":
        continue
    relative = path.relative_to(target).as_posix()
    assert path.suffix.lower() not in (".db", ".sqlite", ".csv"), relative
    parts = path.relative_to(target).parts
    # Third-party license trees can legitimately preserve paths such as numpy/_core/src.
    if "licenses" not in parts:
        assert not any(part in ("tests", ".venv", "data", "src") for part in parts), relative
    files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
(target / "manifest.json").write_text(json.dumps({"versions": versions, "sha256": files}, indent=2), encoding="utf-8")
print(f"Portable package verified: {len(files)} files; no databases, CSVs, tests or source folders.")
