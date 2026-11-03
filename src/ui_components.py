"""Retail Data Studio design tokens and small reusable Widgets components."""
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QByteArray
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QWidget, QScrollArea, QSizePolicy, QLayout, QGraphicsDropShadowEffect,
)

INK = "#152035"
ACCENT = "#6269D8"
TEXT = "#17233C"
MUTED = "#69778B"
LINE = "#E4E7EF"
METRIC_COLORS = {"Transactions": "#3478C7", "Units_Sold": "#16877E", "Estimated Revenue": ACCENT}


def icon(name, color=MUTED):
    """Original, consistent 24px line icons; no external assets or fonts."""
    paths = {
        "import": '<path d="M12 3v12m-4-4 4 4 4-4M4 15v5h16v-5"/>',
        "reports": '<path d="M4 4v16h17M8 15v-4m5 4V7m5 8v-6"/>',
        "folder": '<path d="M3 7h7l2 2h9v11H3zM3 7V4h7l2 3"/>',
        "arrow": '<path d="M5 12h14m-5-5 5 5-5 5"/>',
        "file": '<path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6m-6 4h6"/>',
        "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
        "refresh": '<path d="M20 7v5h-5M4 17v-5h5M5 8a8 8 0 0 1 14-2m0 10a8 8 0 0 1-14 2"/>',
        "units": '<path d="m12 3 9 5v9l-9 5-9-5V8zm-9 5 9 5 9-5m-9 5v9M7 5l10 6"/>',
        "revenue": '<rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="12" cy="12" r="3"/><path d="M6 12h1m10 0h1"/>',
        "store": '<path d="M4 10v11h16V10M3 10l2-7h14l2 7M9 21v-7h6v7M3 10q3 4 6 0 3 4 6 0 3 4 6 0"/>',
    }
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
           f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" '
           f'stroke-linecap="round" stroke-linejoin="round">{paths[name]}</svg>')
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


def label(text, role="body"):
    widget = QLabel(text)
    widget.setProperty("role", role)
    widget.setWordWrap(True)
    return widget


def action(text, glyph=None, primary=False):
    button = QPushButton(text)
    button.setCursor(Qt.PointingHandCursor)
    button.setProperty("kind", "primary" if primary else "secondary")
    if glyph:
        button.setIcon(icon(glyph, "#FFFFFF" if primary else MUTED))
        button.setIconSize(QSize(18, 18))
    return button


class NavItem(QPushButton):
    def __init__(self, text, glyph):
        super().__init__(text)
        self.setProperty("kind", "nav")
        self.setCheckable(True)
        self.setIcon(icon(glyph, "#C7CDE2"))
        self.setIconSize(QSize(20, 20))
        self.setCursor(Qt.PointingHandCursor)


class BrandMark(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(36, 36)
        self.setAccessibleName("Retail Data Studio")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(ACCENT))
        painter.drawRoundedRect(0, 0, 36, 36, 10, 10)
        painter.setBrush(QColor("#FFFFFF"))
        for x, y, height in ((9, 19, 9), (16, 12, 16), (23, 7, 21)):
            painter.drawRoundedRect(x, y, 4, height, 1.5, 1.5)


class PanelCard(QFrame):
    """Shared panel shell; emphasis is reserved for primary work surfaces."""
    def __init__(self, parent=None, tone="default", elevated=False):
        super().__init__(parent)
        self.setProperty("surface", True)
        self.setProperty("panelTone", tone)
        self.content = QVBoxLayout(self)
        self.content.setContentsMargins(22, 20, 22, 20)
        self.content.setSpacing(16)
        if elevated:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(16)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(21, 32, 53, 18))
            self.setGraphicsEffect(shadow)


class Surface(PanelCard):
    """Compatibility name used by existing screens."""


class PathLabel(QLabel):
    """Elide each path independently; keep the full value accessible and in a tooltip."""
    def __init__(self, text="", role="caption"):
        super().__init__()
        self.setProperty("role", role)
        self.setTextFormat(Qt.PlainText)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(0)
        self.setText(text)

    def setText(self, text):
        self.full_text = text
        self.setToolTip(text)
        self.setAccessibleName(text)
        self._render()

    def _render(self):
        super().setText("\n".join(self.fontMetrics().elidedText(line, Qt.ElideMiddle,
            max(40, self.contentsRect().width())) for line in self.full_text.split("\n")))

    def resizeEvent(self, event):
        self._render()
        super().resizeEvent(event)


class SectionHeader(QFrame):
    def __init__(self, title, subtitle=""):
        super().__init__()
        self.setObjectName("sectionHeader")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(4)
        layout.addWidget(label(title, "section"))
        if subtitle:
            layout.addWidget(label(subtitle, "muted"))


class StatCard(Surface):
    def __init__(self, title, description, accent=False, glyph="reports"):
        super().__init__()
        self.setProperty("accent", accent)
        self.content.setSpacing(9)
        heading = QHBoxLayout()
        heading.addWidget(label(title, "kpiTitle"), 1)
        symbol = QLabel()
        symbol.setObjectName("statIcon")
        symbol.setFixedSize(36, 36)
        symbol.setAlignment(Qt.AlignCenter)
        symbol.setPixmap(icon(glyph, ACCENT).pixmap(QSize(20, 20)))
        heading.addWidget(symbol)
        self.content.addLayout(heading)
        self.value = label("—", "kpiValue")
        self.value.setWordWrap(False)
        self.value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.content.addWidget(self.value)
        self.content.addWidget(label(description, "caption"))
        self.trend = label("", "trend")
        self.trend.hide()
        self.content.addWidget(self.trend)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_trend(self, text="", direction="neutral"):
        """Only show a delta when the caller supplies an actual comparison."""
        self.trend.setText(text)
        self.trend.setProperty("direction", direction)
        self.trend.style().unpolish(self.trend)
        self.trend.style().polish(self.trend)
        self.trend.setVisible(bool(text))


class KpiCard(StatCard):
    """Compatibility for import metrics."""


class FilterPanel(PanelCard):
    def __init__(self):
        super().__init__(tone="filters")
        self.content.addWidget(SectionHeader("Report controls", "Dönemi belirleyin, verinizi mağaza ve kategoriye göre daraltın."))


class DataTableCard(PanelCard):
    def __init__(self, title, subtitle):
        super().__init__()
        self.content.addWidget(SectionHeader(title, subtitle))


class FilterChips(QWidget):
    """A compact ribbon, reflowing to two rows in narrow workspaces."""
    def __init__(self):
        super().__init__()
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(6)
        self.chips = []
        for index in range(4):
            chip = PathLabel()
            chip.setObjectName("filterChip")
            chip.setMinimumHeight(26)
            self.chips.append(chip)
            self.grid.addWidget(chip, index // 2, index % 2)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

    def set_values(self, values):
        for chip, value in zip(self.chips, values):
            chip.setText(value)

    def resizeEvent(self, event):
        columns = 4 if event.size().width() >= 760 else 2
        while self.grid.count():
            self.grid.takeAt(0)
        for column in range(4):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        for index, chip in enumerate(self.chips):
            self.grid.addWidget(chip, index // columns, index % columns)
        super().resizeEvent(event)


class AdaptiveGrid(QWidget):
    """Four columns on desktop; two on narrow/high-DPI workspaces."""
    def __init__(self, widgets, breakpoint=760):
        super().__init__()
        self.widgets = widgets
        self.breakpoint = breakpoint
        self.columns = 0
        self.grid = QGridLayout(self)
        self.grid.setSizeConstraint(QLayout.SetNoConstraint)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.reflow(4)

    def minimumSizeHint(self):
        # The previous four-column minimum must not prevent the narrow reflow.
        return QSize(0, self.grid.minimumSize().height())

    def reflow(self, columns):
        if columns == self.columns:
            return
        self.columns = columns
        while self.grid.count():
            self.grid.takeAt(0)
        for column in range(4):
            self.grid.setColumnStretch(column, 0)
        for index, widget in enumerate(self.widgets):
            self.grid.addWidget(widget, index // columns, index % columns)
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)

    def resizeEvent(self, event):
        self.reflow(4 if event.size().width() >= self.breakpoint else 2)
        super().resizeEvent(event)


class StatusBanner(QLabel):
    def __init__(self, text=""):
        super().__init__()
        self.setObjectName("statusBanner")
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setText(text)

    def setText(self, text):
        lower = text.lower()
        tone = "neutral"
        if "satış bulunamadı" in lower or "geçerli bir csv" in lower or "sonra olamaz" in lower:
            tone = "warning"
        elif any(word in lower for word in ("başarısız", "bulunamadı", "başlatılamadı", "oluşturulamadı")):
            tone = "error"
        elif any(word in lower for word in ("tamamlandı", "rapor hazır")):
            tone = "success"
        elif any(word in lower for word in ("çalışıyor", "hazırlanıyor", "başlatılıyor", "yazılıyor")):
            tone = "working"
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)
        super().setText(text)


class StepFlow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.steps = []
        for index, title in enumerate(("Validation", "Incremental Load", "Generate Reports")):
            step = label(f"0{index + 1}  {title}")
            step.setObjectName("pipelineStep")
            layout.addWidget(step, 1)
            self.steps.append(step)
        self.update_steps(0)

    def update_steps(self, completed, running=False, failed=False):
        for index, step in enumerate(self.steps):
            state = "done" if index < completed else "pending"
            if index == completed:
                state = "error" if failed else "active" if running else "pending"
            step.setProperty("state", state)
            title = ("Validation", "Incremental Load", "Generate Reports")[index]
            status = {"done": "Tamamlandı", "pending": "Bekliyor", "active": "İşleniyor", "error": "Başarısız"}[state]
            step.setText(f"0{index + 1}  {title}\n{status}")
            step.style().unpolish(step)
            step.style().polish(step)


def field(title, widget):
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    caption = label(title, "caption")
    caption.setBuddy(widget)
    widget.setAccessibleName(title.replace("&", ""))
    layout.addWidget(caption)
    layout.addWidget(widget)
    return container


def scroll_page(widget):
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(widget)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    return scroll


STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #17233C; }
QMainWindow, QScrollArea, QWidget#workspace, QWidget#page { background: #F1F3F8; }
QLabel { background: transparent; }
QLabel[role='pageTitle'] { font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }
QLabel[role='section'] { font-size: 16px; font-weight: 600; }
QLabel[role='muted'], QLabel[role='caption'] { color: #69778B; }
QLabel[role='caption'] { font-size: 12px; }
QLabel[role='eyebrow'] { color: #6269D8; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; }
QLabel[role='kpiTitle'] { color: #57657B; font-size: 12px; font-weight: 600; }
QLabel[role='kpiValue'] { font-size: 32px; font-weight: 700; letter-spacing: -1px; }
QLabel#statIcon { background: #EEEFFC; border: 1px solid #E0E2F7; border-radius: 11px; }
QLabel#filterChip { background: #EDEFF7; color: #4F5D78; padding: 3px 9px; border-radius: 8px; font-size: 11px; }
QLabel[role='trend'] { color: #69778B; font-size: 12px; }
QLabel[direction='up'] { color: #16806A; }
QLabel[direction='down'] { color: #B45264; }
QFrame[surface='true'] { background: #FFFFFF; border: 1px solid #D8DEEA; border-radius: 14px; }
QFrame[panelTone='filters'] { background: #F8F9FD; border-color: #CCD3E4; }
QFrame[panelTone='analytics'] { border-color: #CCD3E4; }
QFrame[accent='true'] { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F5F3FF,stop:1 #E9EDFF); border: 1px solid #BBC2EC; }
QFrame[accent='true'] QLabel[role='kpiValue'] { color: #454CB0; }
QFrame#sectionHeader { background: transparent; border: none; border-bottom: 1px solid #E7EAF2; border-radius: 0; }
QFrame#fileDrop { background: #F7F8FE; border: 1px dashed #9CA5D6; border-radius: 12px; }
QFrame#sidebar { background: #152035; border: none; }
QFrame#workspaceCard { background: #1D2B43; border: 1px solid #35435C; border-radius: 12px; }
QFrame#sidebar QLabel { color: #C4CCDE; }
QFrame#sidebar QLabel[role='brand'] { color: #FFFFFF; font-size: 17px; font-weight: 600; }
QFrame#sidebar QLabel[role='caption'] { color: #A9B4CB; font-size: 11px; }
QFrame#sidebar QComboBox { background: #202E47; color: #FFFFFF; border: 1px solid #35435C; }
QPushButton { padding: 10px 14px; border: 1px solid #DDE1EA; border-radius: 7px; background: #FFFFFF; font-weight: 600; }
QPushButton:hover { background: #F0F1FC; border-color: #B7BCE6; }
QPushButton:pressed { background: #E2E5F9; }
QPushButton:focus, QComboBox:focus, QDateEdit:focus, QLineEdit:focus, QTableView:focus { border: 2px solid #6269D8; }
QPushButton[kind='primary'] { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7176E6,stop:1 #5158BD); color: #FFFFFF; border: 1px solid #5D63CD; border-radius: 9px; padding: 11px 18px; }
QPushButton[kind='primary']:hover { background: #5158C4; }
QPushButton:disabled { color: #8D96A8; background: #EFF1F6; border-color: #E4E7EF; }
QPushButton[kind='nav'] { text-align: left; border: 1px solid transparent; color: #B8C3D9; background: transparent; padding: 13px 14px; font-weight: 500; }
QPushButton[kind='nav']:hover { background: #273651; color: #FFFFFF; }
QPushButton[kind='nav']:checked { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #40477A,stop:1 #2C395B); color: #FFFFFF; border: 1px solid #505B89; border-left: 3px solid #A7ABFF; font-weight: 600; }
QPushButton[kind='nav']:focus { border: 1px solid #9298FF; }
QComboBox, QDateEdit, QLineEdit { background: #FFFFFF; border: 1px solid #DDE1EA; border-radius: 6px; padding: 8px 10px; min-height: 18px; selection-background-color: #E3E5FA; }
QComboBox:disabled, QDateEdit:disabled { color: #8D96A8; background: #F1F3F7; }
QComboBox::drop-down { width: 22px; border: none; }
QComboBox QAbstractItemView { background: #FFFFFF; color: #17233C; selection-background-color: #E8EAFB; selection-color: #17233C; padding: 4px; }
QLabel#statusBanner { padding: 10px 12px; border-radius: 7px; background: #EDF0F7; color: #53627A; }
QLabel#statusBanner[tone='success'] { background: #EAF6F0; color: #237354; }
QLabel#statusBanner[tone='error'] { background: #FCEEEF; color: #A23D4B; }
QLabel#statusBanner[tone='working'] { background: #EFEEFC; color: #5057B5; }
QLabel#statusBanner[tone='warning'] { background: #FFF4E3; color: #8F601C; }
QLabel#pipelineStep { padding: 14px 12px; background: #F7F8FB; color: #69778B; border: 1px solid #E1E5EE; border-radius: 10px; }
QLabel#pipelineStep[state='active'] { background: #F0EFFD; color: #5057B5; border-color: #B7BBEB; }
QLabel#pipelineStep[state='done'] { background: #EFF8F3; color: #237354; border-color: #BEDDCD; }
QLabel#pipelineStep[state='error'] { background: #FCEEEF; color: #A23D4B; border-color: #E8BCC3; }
QProgressBar { background: #EDF0F7; border: none; border-radius: 3px; max-height: 5px; }
QProgressBar::chunk { background: #6269D8; border-radius: 3px; }
QPlainTextEdit { background: #F8F9FC; border: 1px solid #E4E7EF; border-radius: 7px; padding: 10px; font-family: 'Cascadia Code', 'Consolas'; font-size: 12px; }
QTableView { background: #FFFFFF; alternate-background-color: #F8F9FC; border: none; gridline-color: #EDF0F5; selection-background-color: #EFEEFC; selection-color: #17233C; }
QTableView::item { padding: 6px 10px; border-bottom: 1px solid #EDF0F6; }
QTableView::item:hover { background: #EDF0FB; }
QListWidget { background: #FFFFFF; border: 1px solid #E4E7EF; border-radius: 8px; outline: none; }
QListWidget::item { padding: 14px; margin: 4px; border: 1px solid #E2E6EF; border-radius: 9px; }
QListWidget::item:selected { background: #EFEEFC; color: #5057B5; border: 1px solid #B7BBEB; }
QListWidget::item:hover { background: #F6F7FB; }
QListWidget:focus { border: 2px solid #6269D8; }
QHeaderView::section { background: #EFF2F8; color: #445470; border: none; border-bottom: 1px solid #DCE2EE; padding: 12px 10px; font-size: 12px; font-weight: 600; }
QTabWidget::pane { border: none; background: #FFFFFF; }
QTabBar::tab { background: #F3F5FA; color: #69778B; padding: 10px 20px; margin: 0 4px 10px 0; border-radius: 8px; border: 1px solid transparent; }
QTabBar::tab:selected { color: #5057B5; background: #EEEFFC; border: 1px solid #CCD1F1; font-weight: 600; }
QTabBar::tab:hover { background: #F4F5FB; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #CAD0DF; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QToolTip { background: #17233C; color: #FFFFFF; border: none; padding: 8px; }
"""
STYLE += ('QComboBox::down-arrow, QDateEdit::down-arrow { image: url("' +
          (Path(__file__).parent / "assets/chevron-down.svg").as_posix() +
          '"); width: 12px; height: 12px; }')
