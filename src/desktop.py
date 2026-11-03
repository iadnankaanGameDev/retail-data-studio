"""Desktop entry point. ETL runs in a separate process, never on the UI thread."""
import codecs
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QProcess, QProcessEnvironment, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QVBoxLayout, QWidget, QStackedWidget, QFrame, QButtonGroup,
)
from projects import PROJECTS
from project_manager import DEFAULT_STORE, load_projects
from projects_view import ProjectsView
from paths import BASE_DIR
from texts import tr
from runtime import worker_command, APP_VERSION, hold_instance_mutex
from combo_box import ReadableComboBox
from filesystem import fs_path
from reports_view import ReportsView
from ui_components import (STYLE, BrandMark, NavItem, Surface, SectionHeader, KpiCard,
    AdaptiveGrid, StatusBanner, StepFlow, PathLabel, label, action, scroll_page)


class MainWindow(QMainWindow):
    def __init__(self, projects=None, project_store=DEFAULT_STORE):
        super().__init__()
        self.project_store = Path(project_store)
        saved, self.project_errors = load_projects(project_store) if projects is None else ([], [])
        self.projects = list(PROJECTS) + saved if projects is None else list(projects)
        projects = self.projects
        self.process = None
        self.output_dir = None
        self.source = None
        self.setWindowTitle(f"Retail Data Studio • V{APP_VERSION}")
        self.resize(1280, 820)
        self.setMinimumSize(720, 460)
        screen = QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            self.resize(min(1280, available.width() - 32), min(820, available.height() - 48))
        body = QWidget()
        body.setObjectName("workspace")
        self.setCentralWidget(body)
        shell = QHBoxLayout(body)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(224)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(18, 26, 18, 22)
        side.setSpacing(12)
        brand = QHBoxLayout()
        brand.addWidget(BrandMark())
        brand.addWidget(label("Retail Data\nStudio", "brand"), 1)
        side.addLayout(brand)
        side.addSpacing(28)
        workspace_card = QFrame()
        workspace_card.setObjectName("workspaceCard")
        workspace_layout = QVBoxLayout(workspace_card)
        workspace_layout.setContentsMargins(12, 14, 12, 14)
        workspace_layout.setSpacing(10)
        workspace_layout.addWidget(label("ACTIVE WORKSPACE", "caption"))
        self.project_box = ReadableComboBox(dark=True)
        self.project_box.setMinimumContentsLength(8)
        self.project_box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.project_box.setAccessibleName("Aktif proje")
        for project in projects:
            self.project_box.addItem(project.name)
        workspace_layout.addWidget(self.project_box)
        self.description = label("", "caption")
        workspace_layout.addWidget(self.description)
        side.addWidget(workspace_card)
        self.project_details = NavItem(tr("project.details"), "info")
        self.project_details.setCheckable(False)
        self.project_details.clicked.connect(self.show_project_details)
        side.addWidget(self.project_details)
        side.addSpacing(20)
        side.addWidget(label("WORKSPACE TOOLS", "caption"))
        self.nav_group = QButtonGroup(self)
        self.nav_items = []
        for index, (title, glyph) in enumerate(((tr("nav.import"), "import"), (tr("nav.reports"), "reports"), (tr("nav.projects"), "folder"))):
            button = NavItem(title, glyph)
            self.nav_group.addButton(button, index)
            self.nav_items.append(button)
            side.addWidget(button)
        side.addStretch(1)
        side.addWidget(label("LOCAL WORKSPACE", "caption"))
        side.addWidget(label(f"Retail Data Studio  /  {APP_VERSION}", "caption"))
        shell.addWidget(self.sidebar)
        self.pages = QStackedWidget()
        shell.addWidget(self.pages, 1)
        self.nav_group.idClicked.connect(self.pages.setCurrentIndex)
        self.pages.currentChanged.connect(lambda index: self.nav_items[index].setChecked(True))
        self.nav_items[0].setChecked(True)
        # Kept as an internal compatibility alias; navigation is now a stacked workspace.
        self.tabs = self.pages
        processing = QWidget()
        processing.setObjectName("page")
        layout = QVBoxLayout(processing)
        layout.setContentsMargins(28, 26, 28, 28)
        layout.setSpacing(18)
        layout.addWidget(label("WORKSPACE  /  DATA OPERATIONS", "eyebrow"))
        layout.addWidget(label(tr("nav.import"), "pageTitle"))
        layout.addWidget(label("Satış verilerinizi doğrulayın, güvenle yükleyin ve raporlamaya hazır hale getirin.", "muted"))
        self.database_label = label("", "caption")
        layout.addWidget(self.database_label)
        upload = Surface(elevated=True)
        upload.content.addWidget(SectionHeader("Bring your sales data", "CSV dosyanızı seçin. Kaynak dosya değiştirilmez."))
        drop = QFrame()
        drop.setObjectName("fileDrop")
        drop_layout = QVBoxLayout(drop)
        drop_layout.setContentsMargins(24, 24, 24, 24)
        drop_layout.setSpacing(12)
        drop_layout.addWidget(label("CSV  /  SALES DATA", "eyebrow"))
        self.selected_file = PathLabel("İşlenecek dosyayı seçin", "section")
        drop_layout.addWidget(self.selected_file)
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("CSV dosyasının yolu")
        self.file_edit.setAccessibleName("CSV dosyası yolu")
        self.file_edit.hide()
        self.file_edit.textChanged.connect(self.file_changed)
        drop_layout.addWidget(self.file_edit)
        self.browse_button = action(tr("import.choose"), "folder")
        self.browse_button.clicked.connect(self.choose_file)
        file_row = QHBoxLayout()
        file_row.addWidget(self.browse_button)
        file_row.addStretch()
        drop_layout.addLayout(file_row)
        drop_layout.addWidget(label("Required columns  •  Sale_ID, Date, Store_ID, Product_ID, Units", "caption"))
        upload.content.addWidget(drop)
        upload.content.addWidget(label("İşlemi başlat, geçerli yeni kayıtları seçili projenin veritabanına ekler.", "muted"))
        row = QHBoxLayout()
        self.start_button = action(tr("import.start"), "arrow", primary=True)
        self.start_button.clicked.connect(self.start_processing)
        self.open_button = action(tr("import.outputs"), "folder")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_output)
        row.addWidget(self.start_button)
        row.addWidget(self.open_button)
        row.addStretch()
        upload.content.addLayout(row)
        layout.addWidget(upload)
        flow = Surface()
        flow.content.addWidget(SectionHeader("Processing pipeline", "Üç aşama. Her adımda görünür sonuçlar."))
        self.step_flow = StepFlow()
        flow.content.addWidget(self.step_flow)
        self.progress = QProgressBar()
        self.progress.setRange(0, 3)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        flow.content.addWidget(self.progress)
        self.status_label = StatusBanner("Hazır • Bir CSV dosyası seçin.")
        flow.content.addWidget(self.status_label)
        layout.addWidget(flow)
        self.metrics = {}
        cards = []
        for key, title, caption in (
            ("validation_accepted", "Accepted", "Doğrulamayı geçen"),
            ("validation_rejected", "Rejected", "Kontrol gerektiren"),
            ("new_records", "New records", "Veritabanına eklenen"),
            ("already_present", "Already present", "Tekrar yüklenmeyen"),
        ):
            card = KpiCard(title, caption)
            cards.append(card)
            self.metrics[key] = card.value
        layout.addWidget(AdaptiveGrid(cards))
        log_panel = Surface(tone="filters")
        self.log_toggle = action("Technical log  +")
        self.log_toggle.setCheckable(True)
        log_panel.content.addWidget(self.log_toggle, 0, Qt.AlignLeft)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2500)
        self.log.setMinimumHeight(220)
        self.log.hide()
        self.log_toggle.toggled.connect(self.log.setVisible)
        self.log_toggle.toggled.connect(lambda opened: self.log_toggle.setText("Technical log  −" if opened else "Technical log  +"))
        log_panel.content.addWidget(self.log)
        layout.addWidget(log_panel)
        layout.addStretch()
        self.import_scroll = scroll_page(processing)
        self.pages.addWidget(self.import_scroll)
        self.reports = ReportsView()
        self.pages.addWidget(scroll_page(self.reports))
        self.project_manager = ProjectsView(self.project_store, BASE_DIR)
        self.pages.addWidget(scroll_page(self.project_manager))
        self.project_manager.created.connect(self.register_project)
        self.project_manager.activate.connect(self.activate_project)
        self.project_manager.busy_changed.connect(self.update_busy)
        self.reports.busy_changed.connect(self.update_busy)
        self.project_box.currentIndexChanged.connect(self.update_project)
        self.update_project()

    def register_project(self, project):
        self.projects.append(project)
        self.project_box.addItem(project.name)
        self.project_box.setCurrentIndex(len(self.projects) - 1)

    def activate_project(self, key):
        if self.process is not None or self.reports.busy or self.project_manager.busy:
            return
        for index, project in enumerate(self.projects):
            if project.key == key:
                self.project_box.setCurrentIndex(index)
                break

    def resizeEvent(self, event):
        if hasattr(self, "sidebar"):
            self.sidebar.setFixedWidth(184 if event.size().width() < 1050 else 224)
        super().resizeEvent(event)

    def file_changed(self, filename):
        self.selected_file.setText(Path(filename).name if filename else "İşlenecek dosyayı seçin")
        self.selected_file.setToolTip(filename)

    def show_project_details(self):
        if self.project is None:
            return
        QMessageBox.information(self, "Project details",
            f"{self.project.name}\n\nDatabase\n{self.project.database}\n\nOutputs\n{self.project.output_root}")

    @property
    def project(self):
        index = self.project_box.currentIndex()
        return self.projects[index] if 0 <= index < len(self.projects) else None

    def update_project(self):
        if self.project is None:
            self.description.setText("İlk projenizi oluşturun")
            self.database_label.setText("Henüz proje yok. Projeler ekranından bir Sales ETL projesi oluşturun.")
            self.project_details.setEnabled(False)
            self.project_manager.refresh_projects([], "", self.project_errors)
            self.pages.setCurrentIndex(2)
            self.update_busy()
            return
        self.project_details.setEnabled(True)
        self.project_box.setToolTip(self.project.name)
        self.description.setText("Demo environment" if "demo" in self.project.key else "Production workspace")
        self.database_label.setText(f"{self.project.name}  /  {self.project.database.name}")
        self.database_label.setToolTip(str(self.project.database))
        self.project_details.setToolTip(str(self.project.database))
        self.output_dir = None
        self.open_button.setEnabled(False)
        self.log.clear()
        self.progress.setValue(0)
        self.step_flow.update_steps(0)
        self.log_toggle.setChecked(False)
        for metric in self.metrics.values():
            metric.setText("—")
        self.status_label.setText("Hazır • Bir CSV dosyası seçin." if fs_path(self.project.database).is_file()
                                  else "Veritabanı bulunamadı. Otomatik oluşturulmaz veya kopyalanmaz.")
        self.file_edit.clear()
        self.reports.set_project(self.project)
        self.project_manager.refresh_projects(self.projects, self.project.key, self.project_errors)
        self.update_busy()

    def choose_file(self):
        if self.project is None:
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Satış CSV dosyasını seç", str(self.project.incoming_dir),
            "CSV dosyaları (*.csv *.CSV)")
        if filename:
            self.file_edit.setText(filename)

    def update_busy(self, *_):
        busy = self.process is not None or self.reports.busy or self.project_manager.busy
        for widget in (self.project_box, self.file_edit, self.browse_button, self.start_button):
            widget.setEnabled(not busy and self.project is not None)
        self.reports.setEnabled(self.project is not None and self.process is None and not self.project_manager.busy)
        self.project_manager.setEnabled(self.process is None and not self.reports.busy)

    def start_processing(self):
        if self.project is None:
            return
        if self.process is not None or self.reports.busy or self.project_manager.busy:
            return
        source = Path(self.file_edit.text().strip()).expanduser().resolve()
        if not fs_path(source).is_file() or source.suffix.lower() != ".csv":
            self.status_label.setText("Geçerli bir CSV dosyası seçin.")
            return
        if not fs_path(self.project.database).is_file():
            self.status_label.setText("Veritabanı bulunamadı. Proje kurulumunu kontrol edin.")
            return
        self.source = source
        self.output_dir = self.project.output_root / (
            datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8])
        try:
            fs_path(self.output_dir).mkdir(parents=True)
        except OSError as exc:
            self.status_label.setText(f"Çıktı klasörü oluşturulamadı: {exc}")
            return
        self.log.clear()
        self.progress.setValue(0)
        self.step_flow.update_steps(0)
        self.log_toggle.setChecked(False)
        for metric in self.metrics.values():
            metric.setText("—")
        self.open_button.setEnabled(True)
        self.status_label.setText("Başlatılıyor…")
        self.step_flow.update_steps(0, running=True)
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.pending_line = ""
        process = QProcess(self)
        self.process = process
        self.reports.invalidate()
        self.update_busy()
        process.setWorkingDirectory(str(Path(sys.executable).parent))
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONIOENCODING", "utf-8")
        environment.insert("PYTHONUTF8", "1")
        process.setProcessEnvironment(environment)
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.readyReadStandardOutput.connect(self.read_output)
        process.finished.connect(self.finished)
        process.errorOccurred.connect(self.process_error)
        command = worker_command(self.project.entrypoint)
        process.start(command[0], command[1:] + [source.name,
            "--incoming-dir", str(source.parent),
            "--db-path", str(self.project.database),
            "--output-dir", str(self.output_dir),
            "--reference-dir", str(self.project.reference_dir),
            "--quarantine-dir", str(self.project.quarantine_dir / self.output_dir.name
                                    if self.project.managed else self.output_dir / "quarantine"),
            "--log-dir", str(self.output_dir / "logs"),
        ])

    def read_output(self):
        text = self.decoder.decode(bytes(self.process.readAllStandardOutput()))
        self.consume_text(text)

    def consume_text(self, text):
        self.pending_line += text
        while "\n" in self.pending_line:
            line, self.pending_line = self.pending_line.split("\n", 1)
            self.log.appendPlainText(line.rstrip())
            if line.startswith("[START]"):
                self.status_label.setText(line.replace("[START]", "Çalışıyor:"))
                self.step_flow.update_steps(self.progress.value(), running=True)
            if line.startswith("[SUCCESS]"):
                self.progress.setValue(min(3, self.progress.value() + 1))
                self.step_flow.update_steps(self.progress.value())
                self.read_metrics()

    def read_metrics(self):
        # Per-run folders prevent stale results from appearing after a failed run.
        for suffix in ("validation", "load"):
            path = self.output_dir / f"{self.source.stem}_{suffix}_summary.json"
            if fs_path(path).is_file():
                try:
                    summary = json.loads(fs_path(path).read_text(encoding="utf-8"))
                    if summary.get("source_file") == self.source.name:
                        for key, widget in self.metrics.items():
                            if key in summary:
                                widget.setText(str(summary[key]))
                except (OSError, ValueError) as exc:
                    self.log.appendPlainText(f"Özet okunamadı: {exc}")

    def finished(self, exit_code, exit_status):
        self.read_output()
        self.consume_text(self.decoder.decode(b"", final=True) + "\n")
        self.read_metrics()
        success = exit_code == 0 and exit_status == QProcess.NormalExit
        self.status_label.setText(
            "Tamamlandı • Raporlar ve reddedilen kayıtlar işlem çıktılarında."
            if success else
            "İşlem başarısız • Günlük ayrıntılarını inceleyin. Raporlama hatası, "
            "önceden tamamlanan yüklemeyi geri almaz. Eklenen kayıt sayısını kontrol edin.")
        self.step_flow.update_steps(self.progress.value(), failed=not success)
        if not success:
            self.log_toggle.setChecked(True)
        self.release_process()

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.log.appendPlainText(self.process.errorString())
            self.status_label.setText("Python işlemi başlatılamadı. Günlüğü inceleyin.")
            self.step_flow.update_steps(0, failed=True)
            self.log_toggle.setChecked(True)
            self.release_process()

    def release_process(self):
        self.process.deleteLater()
        self.process = None
        self.update_busy()

    def open_output(self):
        if self.output_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))

    def closeEvent(self, event):
        if self.process is not None or self.reports.busy or self.project_manager.busy:
            QMessageBox.information(self, "İşlem sürüyor",
                                    "Pencereyi kapatmadan önce etkin işlemin tamamlanmasını bekleyin.")
            event.ignore()
        else:
            event.accept()



def main():
    hold_instance_mutex()
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "assets/retail.ico")))
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
