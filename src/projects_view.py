"""Project selection and explicit creation using the shared V2.1 components."""
from filesystem import fs_path
from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QMessageBox, QInputDialog

from project_manager import create_project
from project_backup import backup_project, restore_project
from reports_view import BackgroundTask
from texts import tr
from ui_components import Surface, SectionHeader, StatusBanner, PathLabel, field, label, action, icon, ACCENT


class ProjectsView(QWidget):
    activate = Signal(str)
    created = Signal(object)
    busy_changed = Signal(bool)

    def __init__(self, store, pipeline_root, parent=None):
        super().__init__(parent)
        self.store = Path(store)
        self.pipeline_root = Path(pipeline_root)
        self.task = None
        self.projects = []
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 28)
        layout.setSpacing(18)
        layout.addWidget(label(tr("project.title"), "pageTitle"))
        layout.addWidget(label(tr("project.subtitle"), "muted"))
        existing = Surface(elevated=True)
        existing.content.addWidget(SectionHeader("Çalışma alanları", "Bir proje seçin; geçiş yapmak için Projeye geç düğmesini kullanın."))
        self.project_list = QListWidget()
        self.project_list.setMinimumHeight(104)
        self.project_list.setMaximumHeight(230)
        self.project_list.setAccessibleName("Kayıtlı projeler")
        self.project_list.setTextElideMode(Qt.ElideMiddle)
        self.project_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        existing.content.addWidget(self.project_list)
        self.details = PathLabel()
        existing.content.addWidget(self.details)
        self.switch = action(tr("project.activate"), "arrow")
        self.switch.clicked.connect(self.activate_selected)
        existing.content.addWidget(self.switch)
        backup_row = QHBoxLayout()
        self.backup_button = action("Backup Project", "folder")
        self.restore_button = action("Restore Project", "folder")
        self.backup_button.clicked.connect(self.start_backup)
        self.restore_button.clicked.connect(self.start_restore)
        backup_row.addWidget(self.backup_button)
        backup_row.addWidget(self.restore_button)
        existing.content.addLayout(backup_row)
        self.project_list.currentRowChanged.connect(self.show_details)
        layout.addWidget(existing)
        self.form = Surface()
        self.form.content.addWidget(SectionHeader(tr("project.create"), tr("project.template")))
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(100)
        self.name_edit.setPlaceholderText("Örn. Ankara satışları")
        self.form.content.addWidget(field(tr("project.name"), self.name_edit))
        self.form.content.addWidget(SectionHeader("Referans katalogları", "Yalnızca Sales ETL Template ile uyumlu CSV dosyalarını seçin."))
        self.products_edit = self.file_field(tr("project.products"))
        self.stores_edit = self.file_field(tr("project.stores"))
        self.form.content.addWidget(label(
            "Ürün: Product_ID, Product_Category, Product_Price, Product_Cost\n"
            "Mağaza: Store_ID, Store_Name\n"
            "Satış: Sale_ID, Date, Store_ID, Product_ID, Units", "caption"))
        self.form.content.addWidget(label(tr("project.notice"), "muted"))
        self.form.content.addWidget(PathLabel(f"Proje konumu: {self.store}"))
        self.create_button = action(tr("project.create"), "folder", primary=True)
        self.create_button.clicked.connect(self.start_create)
        self.form.content.addWidget(self.create_button)
        layout.addWidget(self.form)
        self.status = StatusBanner("Yeni projeler Sales ETL Template şemasını kullanır.")
        layout.addWidget(self.status)
        self.diagnostics = label("", "caption")
        layout.addWidget(self.diagnostics)
        layout.addStretch()

    @property
    def busy(self):
        return self.task is not None

    def file_field(self, title):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setAccessibleName(title)
        button = action(tr("project.choose"), "folder")
        button.clicked.connect(lambda: self.choose_file(edit, title))
        row.addWidget(edit, 1)
        row.addWidget(button)
        self.form.content.addWidget(field(title, container))
        return edit

    def choose_file(self, edit, title):
        filename, _ = QFileDialog.getOpenFileName(self, title, "", "CSV (*.csv *.CSV)")
        if filename:
            edit.setText(filename)
            edit.setToolTip(filename)

    def refresh_projects(self, projects, active_key, errors=()):
        self.projects = list(projects)
        self.project_list.blockSignals(True)
        self.project_list.clear()
        for project in projects:
            suffix = f"  •  {tr('project.active')}" if project.key == active_key else ""
            item = QListWidgetItem(icon("folder", ACCENT if suffix else "#69778B"), project.name + suffix)
            item.setToolTip(f"{project.name}{suffix}\n{project.database}")
            if suffix:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor(ACCENT))
            self.project_list.addItem(item)
        index = next((i for i, p in enumerate(projects) if p.key == active_key), 0)
        self.project_list.setCurrentRow(index)
        self.project_list.setMaximumHeight(min(230, max(120, len(projects) * 60 + 8)))
        self.project_list.blockSignals(False)
        self.show_details(index)
        self.diagnostics.setText("\n".join(errors))

    def show_details(self, row):
        self.backup_button.setEnabled(not self.busy and 0 <= row < len(self.projects)
                                      and self.projects[row].managed)
        if 0 <= row < len(self.projects):
            project = self.projects[row]
            self.details.setText(f"{project.description}\nVeritabanı: {project.database}\n"
                                 f"Referanslar: {project.reference_dir}\nÇıktılar: {project.output_root}")

    def activate_selected(self):
        row = self.project_list.currentRow()
        if not self.busy and 0 <= row < len(self.projects):
            self.activate.emit(self.projects[row].key)

    def start_create(self):
        if self.busy:
            return
        name = self.name_edit.text().strip()
        products, stores = self.products_edit.text(), self.stores_edit.text()
        if not name or not fs_path(products).is_file() or not fs_path(stores).is_file():
            self.status.setText("Proje adı ve iki geçerli katalog CSV dosyası gereklidir.")
            return
        self.run_task(lambda: create_project(name, products, stores, self.store, self.pipeline_root),
                      self.creation_succeeded, tr("project.creating"), "Proje oluşturulamadı")

    def start_backup(self):
        row = self.project_list.currentRow()
        if self.busy or not 0 <= row < len(self.projects) or not self.projects[row].managed:
            return
        project = self.projects[row]
        answer = QMessageBox.question(self, "Backup Project",
            f"{project.name}\n\nSatış veritabanının tutarlı SQLite snapshot'ı, ürün ve mağaza "
            "katalogları, proje ayarları ve doğrulama manifesti tek dosyada yedeklenecek.\n\n"
            "İçe aktarılmamış CSV dosyaları ve geçmiş rapor çıktıları dahil değildir. "
            "Raporlar geri yüklenen satışlardan yeniden üretilebilir. Devam edilsin mi?")
        if answer != QMessageBox.Yes:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Yedeği kaydet", "project.rdsbackup",
                                                 "Retail Data Studio Backup (*.rdsbackup)")
        if not filename:
            return
        self.run_task(lambda: backup_project(project, filename),
                      lambda path: self.status.setText(f"Yedekleme tamamlandı. Kaydedilen dosya:\n{path}"),
                      "Yedekleniyor… SQLite snapshot ve SHA-256 kontrolleri hazırlanıyor.", "Yedekleme başarısız")

    def start_restore(self):
        if self.busy:
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Proje yedeğini seç", "",
                                                  "Retail Data Studio Backup (*.rdsbackup)")
        if not filename:
            return
        while True:
            name, accepted = QInputDialog.getText(self, "Restore Project",
                "Yedek doğrulanıp yeni bir kimlikle geri yüklenecek.\nYeni proje adı:")
            if not accepted:
                return
            name = name.strip()
            if name and len(name) <= 100 and not any(ord(c) < 32 for c in name) and not any(
                    p.name.casefold() == name.casefold() for p in self.projects):
                break
            QMessageBox.information(self, "Proje adı", "Geçerli ve mevcut projelerden farklı bir ad seçin.")
        self.run_task(lambda: restore_project(filename, name, self.store, self.pipeline_root),
                      self.restore_succeeded, "Geri yükleniyor… Dosya yapısı, SHA-256 ve SQLite bütünlüğü doğrulanıyor.",
                      "Geri yükleme başarısız; yeni proje oluşturulmadı")

    def restore_succeeded(self, project):
        self.status.setText(f"Proje geri yüklendi: {project.name}\nKonum: {project.root}")
        self.created.emit(project)

    def run_task(self, operation, on_success, message, error_title):
        self.status.setText(message)
        self.form.setEnabled(False)
        self.switch.setEnabled(False)
        self.backup_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.project_list.setEnabled(False)
        self.task = BackgroundTask(operation, self)
        self.task.succeeded.connect(on_success)
        self.task.failed.connect(lambda error: self.status.setText(f"{error_title}: {error}"))
        self.task.finished.connect(self.creation_finished)
        self.busy_changed.emit(True)
        self.task.start()

    def creation_succeeded(self, project):
        self.status.setText(tr("project.created"))
        self.name_edit.clear()
        self.products_edit.clear()
        self.stores_edit.clear()
        self.created.emit(project)

    def creation_finished(self):
        self.task.deleteLater()
        self.task = None
        self.form.setEnabled(True)
        self.switch.setEnabled(True)
        self.restore_button.setEnabled(True)
        self.project_list.setEnabled(True)
        self.show_details(self.project_list.currentRow())
        self.busy_changed.emit(False)
