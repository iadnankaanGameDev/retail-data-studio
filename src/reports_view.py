"""Reusable report tab, table model and background task runner."""
from filesystem import fs_path

from PySide6.QtCore import (QAbstractTableModel, QDate, QModelIndex, QThread,
                            Signal, Qt, QUrl, QSortFilterProxyModel)
from PySide6.QtGui import QDesktopServices
from report_chart import ReportChart
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QDateEdit, QPushButton, QTableView, QTabWidget,
    QHeaderView, QSplitter, QAbstractItemView, QToolTip)

from reporting import (PRESETS, GROUPINGS, METRICS, ReportFilter, date_range,
                       query_report, export_report)
from combo_box import ReadableComboBox as QComboBox
from texts import tr
from ui_components import (Surface, SectionHeader, KpiCard, AdaptiveGrid, StatusBanner,
    label, action, field, ACCENT, MUTED, LINE, StatCard, FilterPanel, FilterChips, DataTableCard, METRIC_COLORS)

HEADERS = {"Transactions": "Sales Transactions", "Units_Sold": "Units Sold",
    "Estimated Revenue": "Estimated Revenue", "Store_ID": "Store ID",
    "Store_Name": "Store", "Product_Category": "Category", "Period": "Period start"}
NUMERIC = {"Transactions", "Units_Sold", "Estimated Revenue", "Store_ID"}


class FrameModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame = None

    def set_frame(self, frame):
        self.beginResetModel()
        self.frame = frame
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or self.frame is None else len(self.frame)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or self.frame is None else len(self.frame.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self.frame is None:
            return None
        value = self.frame.iat[index.row(), index.column()]
        column = self.frame.columns[index.column()]
        if role == Qt.DisplayRole:
            if column == "Estimated Revenue":
                return f"${value:,.2f}"
            return f"{int(value):,}" if column in NUMERIC else str(value)
        if role == Qt.UserRole:
            return float(value) if column in NUMERIC else str(value)
        if role == Qt.TextAlignmentRole:
            return int((Qt.AlignRight if column in NUMERIC else Qt.AlignLeft) | Qt.AlignVCenter)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and self.frame is not None:
            return HEADERS.get(self.frame.columns[section], str(self.frame.columns[section])) if orientation == Qt.Horizontal else str(section + 1)
        if role == Qt.TextAlignmentRole and orientation == Qt.Horizontal and self.frame is not None:
            return int((Qt.AlignRight if self.frame.columns[section] in NUMERIC else Qt.AlignLeft) | Qt.AlignVCenter)


class BackgroundTask(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action

    def run(self):
        try:
            self.succeeded.emit(self.action())
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class ReportsView(QWidget):
    busy_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.setObjectName("page")
        self.result = None
        self.task = None
        self.export_folder = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 28)
        layout.setSpacing(18)
        layout.addWidget(label("WORKSPACE  /  ANALYTICS", "eyebrow"))
        heading = QHBoxLayout()
        heading.addWidget(label(tr("nav.reports"), "pageTitle"), 1)
        self.export = action(tr("reports.export"), "import")
        self.export.setEnabled(False)
        heading.addWidget(self.export)
        self.open_export = action(tr("reports.open"), "folder")
        self.open_export.setEnabled(False)
        heading.addWidget(self.open_export)
        layout.addLayout(heading)
        self.identity = label("", "muted")
        layout.addWidget(self.identity)
        self.kpis = {}
        cards = []
        for key, title, caption in (
            ("Transactions", "Sales Transactions", "Filtrelenen satış kayıtları"),
            ("Units_Sold", "Units Sold", "Toplam satılan ürün adedi"),
            ("Estimated Revenue", "Estimated Revenue", "USD · güncel katalog fiyatları"),
            ("Active Stores", "Active Stores", "Seçimde satış yapan mağazalar"),
        ):
            card = StatCard(title, caption, key == "Estimated Revenue", glyph={
                "Transactions": "reports", "Units_Sold": "units", "Estimated Revenue": "revenue", "Active Stores": "store"}[key])
            cards.append(card)
            self.kpis[key] = card.value
        self.kpi_grid = AdaptiveGrid(cards)
        layout.addWidget(self.kpi_grid)
        self.filters_panel = FilterPanel()
        self.preset = QComboBox()
        self.preset.addItems(PRESETS)
        self.preset.setCurrentText("Tüm zamanlar")
        self.grouping = QComboBox()
        self.grouping.addItems(GROUPINGS)
        self.grouping.setCurrentText("Aylık")
        self.store = QComboBox()
        self.store.setMinimumContentsLength(10)
        self.store.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.store.addItem("Tüm mağazalar", None)
        self.category = QComboBox()
        self.category.setMinimumContentsLength(10)
        self.category.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.category.addItem("Tüm kategoriler", None)
        self.filter_grid = AdaptiveGrid([
            field("&Date range", self.preset), field("&Group by", self.grouping),
            field("&Store", self.store), field("&Category", self.category)])
        self.filters_panel.content.addWidget(self.filter_grid)
        self.custom_dates = QWidget()
        dates = QHBoxLayout(self.custom_dates)
        dates.setContentsMargins(0, 0, 0, 0)
        self.start_date = QDateEdit(QDate.currentDate().addMonths(-12))
        self.end_date = QDateEdit(QDate.currentDate())
        for widget in (self.start_date, self.end_date):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setEnabled(False)
        dates.addWidget(field("Başlangıç (dahil)", self.start_date))
        dates.addWidget(field("Bitiş (dahil)", self.end_date))
        self.custom_dates.hide()
        self.filters_panel.content.addWidget(self.custom_dates)
        filter_footer = QHBoxLayout()
        self.filter_summary = label("", "caption")
        self.filter_summary.hide()
        self.filter_chips = FilterChips()
        filter_footer.addWidget(self.filter_chips, 1)
        self.refresh = action(tr("reports.apply"), "refresh", primary=True)
        filter_footer.addWidget(self.refresh)
        self.filters_panel.content.addLayout(filter_footer)
        layout.addWidget(self.filters_panel)
        self.status = StatusBanner("Filtrelerinizi seçip Filtreleri uygula düğmesine basın.")
        layout.addWidget(self.status)
        chart_surface = Surface(tone="analytics", elevated=True)
        chart_heading = QHBoxLayout()
        chart_heading.addWidget(SectionHeader("Sales performance", "Seçili dönemin ritmi · Tarih aralığı ve gruplama bağımsızdır"), 1)
        self.chart_metric = QComboBox()
        for metric in METRICS:
            self.chart_metric.addItem(HEADERS[metric], metric)
        self.chart_metric.setCurrentText("Estimated Revenue")
        self.chart_metric.setAccessibleName("Grafik ölçüsü")
        chart_heading.addWidget(field("Metric", self.chart_metric), 0, Qt.AlignTop)
        chart_surface.content.addLayout(chart_heading)
        self.chart_view = ReportChart(self)
        self.chart_view.setMinimumHeight(260)
        self.chart_view.setMaximumHeight(340)
        self.chart_view.setAccessibleName("Satış grafiği; aynı değerler Periods tablosunda bulunur")
        self.empty_state = QWidget()
        empty = QVBoxLayout(self.empty_state)
        empty.setContentsMargins(20, 52, 20, 52)
        empty.addWidget(label("Your next insight starts here", "section"), 0, Qt.AlignCenter)
        self.empty_message = label("Proje ve filtreleri seçip Filtreleri uygula ile raporunuzu oluşturun.", "muted")
        self.empty_message.setAlignment(Qt.AlignCenter)
        empty.addWidget(self.empty_message)
        chart_surface.content.addWidget(self.empty_state)
        chart_surface.content.addWidget(self.chart_view)
        chart_surface.content.addWidget(label("Estimated Revenue = adet × güncel ürün fiyatı. Yalnızca satış bulunan dönemler gösterilir.", "caption"))
        layout.addWidget(chart_surface)
        details = DataTableCard("The detail behind the numbers", "Kategori, mağaza ve dönem kırılımları · Sıralamak için kolon başlıklarını seçin.")
        self.tables = QTabWidget()
        self.models = {}
        self.table_views = {}
        for key, title in (("categories", "Categories"), ("stores", "Stores"), ("periods", "Periods")):
            table = QTableView()
            model = FrameModel(table)
            proxy = QSortFilterProxyModel(table)
            proxy.setSourceModel(model)
            proxy.setSortRole(Qt.UserRole)
            table.setModel(proxy)
            table.setSortingEnabled(True)
            table.sortByColumn(-1, Qt.AscendingOrder)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            table.horizontalHeader().setDefaultSectionSize(165)
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().hide()
            table.verticalHeader().setDefaultSectionSize(46)
            table.setMouseTracking(True)
            table.setShowGrid(False)
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setMinimumHeight(240)
            self.models[key] = model
            self.table_views[key] = table
            self.tables.addTab(table, title)
        details.content.addWidget(self.tables)
        layout.addWidget(details)
        layout.addStretch()
        self.preset.currentTextChanged.connect(self.preset_changed)
        for combo in (self.grouping, self.store, self.category):
            combo.currentIndexChanged.connect(self.invalidate)
        for widget in (self.start_date, self.end_date):
            widget.dateChanged.connect(self.invalidate)
        self.refresh.clicked.connect(self.load_report)
        self.export.clicked.connect(self.export_current)
        self.open_export.clicked.connect(self.open_folder)
        self.chart_metric.currentIndexChanged.connect(self.draw_chart)
        self.update_filter_summary()
        self.draw_chart()

    def update_filter_summary(self):
        try:
            filters = self.current_filters()
            interval = f"{filters.start} → {filters.end}" if filters.start else "Tarih sınırı yok"
            self.filter_summary.setText(f"{interval}  ·  {filters.grouping}  ·  "
                f"{self.store.currentText()}  ·  {self.category.currentText()}")
            self.filter_chips.set_values([interval, filters.grouping, self.store.currentText(), self.category.currentText()])
        except ValueError as exc:
            self.filter_summary.setText(str(exc))
            self.filter_chips.set_values([str(exc), "", "", ""])

    @property
    def busy(self):
        return self.task is not None

    def set_project(self, project):
        self.project = project
        self.identity.setText(f"{project.name}  /  Sales analytics · Read-only")
        self.identity.setToolTip(str(project.database))
        for combo, label in ((self.store, "Tüm mağazalar"), (self.category, "Tüm kategoriler")):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(label, None)
            combo.blockSignals(False)
        self.invalidate()
        if not fs_path(project.database).is_file():
            self.status.setText(f"{project.name}: veritabanı bulunamadı. Otomatik oluşturulmaz veya kopyalanmaz.")

    def invalidate(self, *_):
        self.result = None
        self.export_folder = None
        self.export.setEnabled(False)
        self.open_export.setEnabled(False)
        for value in self.kpis.values():
            value.setText("—")
        self.update_filter_summary()
        for model in self.models.values():
            model.set_frame(None)
        self.draw_chart()
        self.status.setText("Seçimler değişti. Güncel sonuçlar için Filtreleri uygula düğmesine basın.")

    def preset_changed(self, preset):
        custom = preset == "Özel tarih aralığı"
        self.custom_dates.setVisible(custom)
        self.start_date.setEnabled(custom)
        self.end_date.setEnabled(custom)
        if not custom:
            start, end = date_range(preset)
            if start:
                self.start_date.setDate(QDate(start.year, start.month, start.day))
                self.end_date.setDate(QDate(end.year, end.month, end.day))
        self.invalidate()

    def current_filters(self):
        if self.preset.currentText() == "Özel tarih aralığı":
            start, end = self.start_date.date().toPython(), self.end_date.date().toPython()
        else:
            start, end = date_range(self.preset.currentText())
        filters = ReportFilter(start, end, self.grouping.currentText(),
                               self.store.currentData(), self.category.currentData())
        filters.validate()
        return filters

    def begin_task(self, action, on_success):
        self.filters_panel.setEnabled(False)
        self.refresh.setEnabled(False)
        self.export.setEnabled(False)
        self.task = BackgroundTask(action, self)
        self.task.succeeded.connect(on_success)
        self.task.failed.connect(lambda message: self.status.setText(f"İşlem başarısız: {message}"))
        self.task.finished.connect(self.task_finished)
        self.busy_changed.emit(True)
        self.task.start()

    def task_finished(self):
        self.task.deleteLater()
        self.task = None
        self.filters_panel.setEnabled(True)
        self.refresh.setEnabled(True)
        self.export.setEnabled(self.result is not None)
        self.busy_changed.emit(False)

    def load_report(self):
        if self.busy or self.project is None:
            return
        self.invalidate()
        try:
            filters = self.current_filters()
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        project = self.project
        self.status.setText("Rapor hazırlanıyor…")
        self.begin_task(lambda: query_report(project, filters), self.show_result)

    def show_result(self, result):
        # Defensive guard in addition to locking the project selector while busy.
        if result.project_key != self.project.key or result.database != str(self.project.database):
            return
        self.result = result
        for combo, options in ((self.store, result.store_options),
                               (self.category, [(c, c) for c in result.category_options])):
            selected = combo.currentData()
            combo.blockSignals(True)
            while combo.count() > 1:
                combo.removeItem(1)
            for value, label in options:
                combo.addItem(f"{label} ({value})" if combo is self.store else label, value)
            index = combo.findData(selected)
            combo.setCurrentIndex(max(0, index))
            combo.blockSignals(False)
        totals = result.totals
        for key, value in self.kpis.items():
            number = len(result.stores) if key == "Active Stores" else totals[key]
            value.setText(f"${number:,.2f}" if key == "Estimated Revenue" else f"{number:,}")
        for key, model in self.models.items():
            model.set_frame(getattr(result, key))
        self.draw_chart()
        message = "Rapor hazır" if totals["Transactions"] else "Bu filtrelerde satış bulunamadı"
        self.status.setText(f"{message}  ·  {len(result.periods)} dönem  ·  {result.project_name}")
        self.status.setToolTip(f"Sorgu: {result.generated_at}. Haftalar pazartesi başlar. Dönem etiketi başlangıç tarihidir.")

    def draw_chart(self, *_):
        metric = self.chart_metric.currentData()
        has_data = self.result is not None and not self.result.periods.empty
        self.chart_view.setVisible(has_data)
        self.empty_state.setVisible(not has_data)
        self.chart_view.set_periods(self.result.periods if has_data else None,
                                   self.result.filters.grouping if has_data else "Aylık", metric)
        if not has_data:
            self.empty_message.setText("Bu filtrelerde satış bulunamadı. Tarih aralığını genişletin veya filtreleri değiştirin."
                if self.result is not None else "Proje ve filtreleri seçip Filtreleri uygula ile raporunuzu oluşturun.")

    def export_current(self):
        if self.busy or self.result is None:
            return
        result, output = self.result, self.project.output_root
        self.status.setText("CSV dosyaları yazılıyor…")
        self.begin_task(lambda: export_report(result, output), self.export_done)

    def export_done(self, folder):
        self.export_folder = folder
        self.open_export.setEnabled(True)
        self.status.setText("CSV aktarımı tamamlandı. Dosyalara Aktarım klasörü ile ulaşabilirsiniz.")
        self.status.setToolTip(str(folder))

    def open_folder(self):
        if self.export_folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.export_folder)))
