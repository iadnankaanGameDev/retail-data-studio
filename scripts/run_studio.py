"""Source launcher: only managed projects, no legacy developer database profiles."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from desktop import QApplication, MainWindow, STYLE
from project_manager import DEFAULT_STORE, load_projects
from PySide6.QtGui import QIcon

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[1] / "src/assets/retail.ico")))
    projects, errors = load_projects(DEFAULT_STORE)
    window = MainWindow(projects=projects, project_store=DEFAULT_STORE)
    window.project_manager.diagnostics.setText("\n".join(errors))
    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
