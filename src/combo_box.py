"""Explicit popup painting keeps Windows selection colors out of themed menus."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPalette, QPen
from PySide6.QtWidgets import (QComboBox, QListView, QStyledItemDelegate, QStyle,
                               QStyleOptionComboBox, QStylePainter)

COLORS = {
    "dark": {"normal": ("#F4F7FF", "#202E47"), "hover": ("#FFFFFF", "#304664"),
             "selected": ("#FFFFFF", "#414BA3"), "disabled": ("#A9B4CB", "#263249"),
             "focus": "#BEC6FF"},
    "light": {"normal": ("#17233C", "#FFFFFF"), "hover": ("#17233C", "#EDF0FC"),
              "selected": ("#17233C", "#DCE2FF"), "disabled": ("#56647A", "#F1F3F7"),
              "focus": "#434CB0"},
}


class PopupDelegate(QStyledItemDelegate):
    def __init__(self, colors, parent):
        super().__init__(parent)
        self.colors = colors

    def paint(self, painter, option, index):
        state = option.state
        key = ("disabled" if not state & QStyle.State_Enabled else
               "selected" if state & QStyle.State_Selected else
               "hover" if state & QStyle.State_MouseOver else "normal")
        foreground, background = self.colors[key]
        painter.save()
        painter.fillRect(option.rect, QColor(background))
        painter.setFont(option.font)
        painter.setPen(QColor(foreground))
        rect = option.rect.adjusted(12, 0, -12, 0)
        text = option.fontMetrics.elidedText(str(index.data(Qt.DisplayRole) or ""), Qt.ElideMiddle, rect.width())
        painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, text)
        if state & QStyle.State_HasFocus:
            painter.setPen(QPen(QColor(self.colors["focus"]), 2))
            painter.drawRect(option.rect.adjusted(1, 1, -2, -2))
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(min(620, option.fontMetrics.horizontalAdvance(str(index.data() or "")) + 24),
                     max(34, option.fontMetrics.height() + 14))


class ReadableComboBox(QComboBox):
    def __init__(self, parent=None, *, dark=False):
        super().__init__(parent)
        self.setMinimumContentsLength(8)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.colors = COLORS["dark" if dark else "light"]
        foreground, background = self.colors["normal"]
        selected_text, selected_bg = self.colors["selected"]
        disabled_text, disabled_bg = self.colors["disabled"]
        hover_text, hover_bg = self.colors["hover"]
        self.setStyleSheet(f"""
            QComboBox {{ color: {foreground}; background: {background}; }}
            QComboBox:hover {{ color: {hover_text}; background: {hover_bg}; }}
            QComboBox:focus, QComboBox:on {{ border: 2px solid {self.colors['focus']}; }}
            QComboBox:disabled {{ color: {disabled_text}; background: {disabled_bg}; }}
        """)
        view = QListView(self)
        view.setMouseTracking(True)
        view.setTextElideMode(Qt.ElideMiddle)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setUniformItemSizes(True)
        view.setStyleSheet(f"""QListView {{ background: {background}; color: {foreground};
            selection-background-color: {selected_bg}; selection-color: {selected_text};
            border: 1px solid {self.colors['focus']}; padding: 2px; outline: none; }}""")
        palette = view.palette()
        for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
            fg, bg = self.colors["disabled" if group == QPalette.Disabled else "normal"]
            for role, color in ((QPalette.Base, bg), (QPalette.Window, bg), (QPalette.Text, fg),
                                (QPalette.WindowText, fg), (QPalette.Highlight, selected_bg),
                                (QPalette.HighlightedText, selected_text)):
                palette.setColor(group, role, QColor(color))
        view.setPalette(palette)
        self.setView(view)
        self.setItemDelegate(PopupDelegate(self.colors, view))
        self.currentTextChanged.connect(self.setToolTip)

    def showPopup(self):
        for index in range(self.count()):
            self.setItemData(index, self.itemText(index), Qt.ToolTipRole)
        screen = self.screen()
        limit = min(640, screen.availableGeometry().width() - 32) if screen else 640
        desired = max((self.fontMetrics().horizontalAdvance(self.itemText(i)) + 44
                       for i in range(self.count())), default=self.width())
        self.view().setFixedWidth(min(limit, max(self.width(), desired)))
        super().showPopup()
        popup = self.view().window()
        popup.setStyleSheet(f"QFrame {{ background: {self.colors['normal'][1]}; }}")
        popup.setFixedWidth(self.view().width() + 6)

    def paintEvent(self, event):
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        rect = self.style().subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxEditField, self)
        option.currentText = self.fontMetrics().elidedText(option.currentText, Qt.ElideMiddle, max(0, rect.width()))
        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.CC_ComboBox, option)
        painter.drawControl(QStyle.CE_ComboBoxLabel, option)
