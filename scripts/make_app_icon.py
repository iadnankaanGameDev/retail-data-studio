"""Build the existing brand mark as a Windows icon without extra dependencies."""
from pathlib import Path
import struct
from PySide6.QtCore import Qt, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter, QColor

image = QImage(256, 256, QImage.Format_ARGB32)
image.fill(Qt.transparent)
painter = QPainter(image)
painter.setRenderHint(QPainter.Antialiasing)
painter.setPen(Qt.NoPen)
painter.setBrush(QColor("#6269D8"))
painter.drawRoundedRect(0, 0, 256, 256, 62, 62)
painter.setBrush(QColor("white"))
for x, y, height in ((64, 135, 64), (114, 85, 114), (164, 50, 149)):
    painter.drawRoundedRect(x, y, 28, height, 9, 9)
painter.end()
data = QByteArray()
buffer = QBuffer(data)
buffer.open(QIODevice.WriteOnly)
assert image.save(buffer, "PNG")
payload = bytes(data)
output = Path(__file__).resolve().parents[1] / "src/assets/retail.ico"
output.write_bytes(struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(payload), 22) + payload)
