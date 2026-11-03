"""Fail-closed Qt native module policy for the chart migration candidate."""
from pathlib import Path

QT_DLLS = {f"qt6{name}.dll" for name in (
    "core", "gui", "widgets", "svg", "network", "opengl", "openglwidgets")}
FORBIDDEN = ("qtcharts", "qt6charts", "virtualkeyboard", "qtgraphs", "qt6graphs",
             "qtqml", "qt6qml", "qtquick", "qt6quick", "qtpdf", "qt6pdf")


def allowed_binary(destination):
    name = destination.replace("\\", "/").lower()
    leaf = name.rsplit("/", 1)[-1]
    if any(token in name for token in FORBIDDEN) or leaf == "qpdf.dll":
        return False
    if leaf.startswith("qt6") and leaf.endswith(".dll"):
        return leaf in QT_DLLS
    return True


def validate_native_dependencies(binaries):
    """Prevent pruning a Qt library still imported by a retained PE binary."""
    import pefile
    names = {Path(dest).name.lower() for dest, _, _ in binaries}
    for destination, source, _ in binaries:
        if Path(source).suffix.lower() not in (".dll", ".pyd", ".exe"):
            continue
        pe = pefile.PE(str(source), fast_load=True)
        try:
            pe.parse_data_directories(directories=[1, 13])
            imports = list(getattr(pe, "DIRECTORY_ENTRY_IMPORT", []))
            imports += list(getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []))
            for entry in imports:
                name = entry.dll.decode("ascii").lower()
                if name.startswith("qt6") and name not in names:
                    raise RuntimeError(f"{destination} still requires excluded/missing {name}")
        finally:
            pe.close()


def audit_folder(folder):
    folder = Path(folder)
    files = [p for p in folder.rglob("*") if p.is_file()]
    forbidden = [str(p.relative_to(folder)) for p in files if not allowed_binary(str(p.relative_to(folder)))]
    if forbidden:
        raise RuntimeError(f"Forbidden Qt files: {forbidden}")
    binaries = [(str(p.relative_to(folder)), str(p), "BINARY") for p in files
                if p.suffix.lower() in (".dll", ".pyd", ".exe")]
    validate_native_dependencies(binaries)
    return sorted(str(p.relative_to(folder)) for p in files if p.suffix.lower() in (".dll", ".pyd"))
