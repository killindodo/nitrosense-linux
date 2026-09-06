"""
Circular arc gauge widget for displaying temperatures and fan RPMs.
Rendered with QPainter for high-DPI crisp antialiased graphics.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QRadialGradient
import math


class CircularGauge(QWidget):
    def __init__(self, title: str = "", unit: str = "°C", min_val: float = 0, max_val: float = 100, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.value: float = min_val
        self.subtext: str = ""
        self.is_rpm = unit.upper() == "RPM"

        self.setMinimumSize(160, 160)

    def set_value(self, val: float, subtext: str = ""):
        self.value = max(self.min_val, min(self.max_val, val))
        self.subtext = subtext
        self.update()

    def _get_color_for_value(self, fraction: float) -> QColor:
        if self.is_rpm:
            # RPM gradient: Blue -> Cyan -> Purple -> Red
            if fraction < 0.4:
                return QColor(0, 180, 255)
            elif fraction < 0.7:
                return QColor(0, 230, 180)
            elif fraction < 0.85:
                return QColor(255, 170, 0)
            else:
                return QColor(255, 46, 76)
        else:
            # Temperature: Cyan (<50°C) -> Yellow (50-75°C) -> Orange -> Crimson (>80°C)
            if self.value < 50:
                return QColor(0, 210, 255)
            elif self.value < 65:
                return QColor(0, 230, 118)
            elif self.value < 78:
                return QColor(255, 179, 0)
            elif self.value < 85:
                return QColor(255, 87, 34)
            else:
                return QColor(255, 23, 68)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        side = min(width, height)

        center_x = width / 2.0
        center_y = height / 2.0
        radius = (side / 2.0) - 16

        rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)

        # Background track arc (240 degrees: from 210 to -30)
        start_angle = 210
        span_total = -240

        pen_bg = QPen(QColor(38, 41, 52), 10)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, int(start_angle * 16), int(span_total * 16))

        # Active value arc
        val_range = max(1.0, self.max_val - self.min_val)
        fraction = (self.value - self.min_val) / val_range
        fraction = max(0.0, min(1.0, fraction))
        active_span = span_total * fraction

        active_color = self._get_color_for_value(fraction)
        pen_fg = QPen(active_color, 10)
        pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_fg)
        painter.drawArc(rect, int(start_angle * 16), int(active_span * 16))

        # Center value text
        painter.setPen(QColor(255, 255, 255))
        font_val = QFont("SansSerif", int(side / 7), QFont.Weight.Bold)
        painter.setFont(font_val)

        if self.is_rpm:
            val_str = f"{int(self.value)}"
        else:
            val_str = f"{self.value:.1f}{self.unit}"

        painter.drawText(
            QRectF(center_x - radius, center_y - radius * 0.45, radius * 2, radius * 0.6),
            Qt.AlignmentFlag.AlignCenter,
            val_str,
        )

        # Title text
        font_title = QFont("SansSerif", max(8, int(side / 17)), QFont.Weight.Medium)
        painter.setFont(font_title)
        painter.setPen(QColor(160, 166, 185))
        painter.drawText(
            QRectF(center_x - radius, center_y + radius * 0.15, radius * 2, radius * 0.4),
            Qt.AlignmentFlag.AlignCenter,
            self.title.upper(),
        )

        # Subtext (e.g. "12W • 530MHz" or "65%")
        if self.subtext:
            font_sub = QFont("SansSerif", max(7, int(side / 20)), QFont.Weight.Normal)
            painter.setFont(font_sub)
            painter.setPen(QColor(120, 126, 145))
            painter.drawText(
                QRectF(center_x - radius, center_y + radius * 0.48, radius * 2, radius * 0.35),
                Qt.AlignmentFlag.AlignCenter,
                self.subtext,
            )

        painter.end()
