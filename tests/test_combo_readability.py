from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QImage, QPainter, QPalette
from PySide6.QtWidgets import QStyle, QStyleOptionViewItem
from test_desktop import app
from combo_box import COLORS, ReadableComboBox
import pytest


def contrast(first, second):
    def luminance(color):
        rgb = QColor(color).getRgbF()[:3]
        rgb = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
        return sum(v * weight for v, weight in zip(rgb, (.2126, .7152, .0722)))
    low, high = sorted((luminance(first), luminance(second)))
    return (high + .05) / (low + .05)


@pytest.mark.parametrize("dark", [False, True])
def test_popup_overrides_hostile_native_palette(app, dark):
    box = ReadableComboBox(dark=dark)
    text = "İstanbul – Şişli, Çığlı Özel Mağaza " * 3
    box.addItem(text)
    box.resize(170, 40)
    box.show()
    box.showPopup()
    app.processEvents()
    assert box.itemData(0, Qt.ToolTipRole) == text
    assert box.toolTip() == text
    assert box.view().width() <= 640 + 10
    colors = box.colors
    states = {"normal": QStyle.State_Enabled, "hover": QStyle.State_Enabled | QStyle.State_MouseOver,
              "selected": QStyle.State_Enabled | QStyle.State_Selected, "disabled": QStyle.State_None}
    for name, state in states.items():
        assert contrast(*colors[name]) >= 4.5
        option = QStyleOptionViewItem()
        option.initFrom(box.view())
        option.rect = QRect(0, 0, 320, 40)
        option.state = state | QStyle.State_HasFocus
        option.palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        option.palette.setColor(QPalette.Highlight, QColor("#FFFFFF"))
        image = QImage(320, 40, QImage.Format_ARGB32)
        painter = QPainter(image)
        box.itemDelegate().paint(painter, option, box.model().index(0, 0))
        painter.end()
        assert image.pixelColor(5, 5).name() == colors[name][1].lower()
        assert image.pixelColor(1, 10).name() == colors["focus"].lower()
    box.hidePopup()
    box.close()


def test_all_report_dropdowns_use_readable_view(app, tmp_path):
    from desktop import MainWindow
    window = MainWindow(projects=[], project_store=tmp_path)
    for widget in (window.project_box, window.reports.preset, window.reports.grouping,
                   window.reports.store, window.reports.category, window.reports.chart_metric):
        assert isinstance(widget, ReadableComboBox)
    window.close()
