"""
Real-time 60-second thermal history graph widget.
Renders antialiased polyline plots for CPU and GPU temperatures.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPolygonF, QLinearGradient
from collections import deque
from typing import Optional


class ThermalGraph(QWidget):
    def __init__(self, max_points: int = 60, parent=None):
        super().__init__(parent)
        self.max_points = max_points
        self.cpu_history = deque(maxlen=max_points)
        self.gpu_history = deque(maxlen=max_points)
        self.setMinimumHeight(130)

    def add_data_point(self, cpu_temp: Optional[float], gpu_temp: Optional[float]):
        self.cpu_history.append(cpu_temp if cpu_temp is not None else 0.0)
        self.gpu_history.append(gpu_temp if gpu_temp is not None else 0.0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Margins
        pad_left = 38
        pad_right = 16
        pad_top = 22
        pad_bottom = 24

        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bottom

        # Background box
        bg_rect = QRectF(pad_left, pad_top, plot_w, plot_h)
        painter.fillRect(bg_rect, QColor(22, 24, 30))

        # Grid lines (at 40°C, 60°C, 80°C, 100°C)
        min_temp = 30.0
        max_temp = 100.0
        temp_range = max_temp - min_temp

        pen_grid = QPen(QColor(42, 45, 56), 1, Qt.PenStyle.DashLine)
        pen_axis = QPen(QColor(80, 85, 105), 1)
        font_axis = QFont("SansSerif", 7)
        painter.setFont(font_axis)

        for temp in [40, 60, 80, 100]:
            y = pad_top + plot_h - ((temp - min_temp) / temp_range) * plot_h
            painter.setPen(pen_grid)
            painter.drawLine(int(pad_left), int(y), int(pad_left + plot_w), int(y))

            painter.setPen(pen_axis)
            painter.drawText(
                QRectF(2, y - 8, pad_left - 6, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{temp}°",
            )

        # Plot points helper
        def get_points(history):
            points = []
            if not history:
                return points
            count = len(history)
            step_x = plot_w / max(1, self.max_points - 1)
            offset_x = (self.max_points - count) * step_x

            for i, val in enumerate(history):
                x = pad_left + offset_x + i * step_x
                clamped_val = max(min_temp, min(max_temp, val))
                y = pad_top + plot_h - ((clamped_val - min_temp) / temp_range) * plot_h
                points.append(QPointF(x, y))
            return points

        cpu_points = get_points(self.cpu_history)
        gpu_points = get_points(self.gpu_history)

        # Draw GPU area & line (Cyan/Blue)
        if len(gpu_points) >= 2:
            poly_gpu = QPolygonF(gpu_points)
            # Area gradient
            grad_gpu = QLinearGradient(0, pad_top, 0, pad_top + plot_h)
            grad_gpu.setColorAt(0, QColor(0, 180, 255, 60))
            grad_gpu.setColorAt(1, QColor(0, 180, 255, 5))

            area_gpu = QPolygonF(gpu_points)
            area_gpu.append(QPointF(gpu_points[-1].x(), pad_top + plot_h))
            area_gpu.append(QPointF(gpu_points[0].x(), pad_top + plot_h))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad_gpu)
            painter.drawPolygon(area_gpu)

            # Line
            pen_gpu = QPen(QColor(0, 210, 255), 2)
            painter.setPen(pen_gpu)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(poly_gpu)

        # Draw CPU area & line (Nitro Crimson Red)
        if len(cpu_points) >= 2:
            poly_cpu = QPolygonF(cpu_points)
            grad_cpu = QLinearGradient(0, pad_top, 0, pad_top + plot_h)
            grad_cpu.setColorAt(0, QColor(255, 46, 76, 70))
            grad_cpu.setColorAt(1, QColor(255, 46, 76, 5))

            area_cpu = QPolygonF(cpu_points)
            area_cpu.append(QPointF(cpu_points[-1].x(), pad_top + plot_h))
            area_cpu.append(QPointF(cpu_points[0].x(), pad_top + plot_h))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad_cpu)
            painter.drawPolygon(area_cpu)

            pen_cpu = QPen(QColor(255, 46, 76), 2)
            painter.setPen(pen_cpu)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(poly_cpu)

        # Graph Border
        painter.setPen(QPen(QColor(48, 52, 65), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(bg_rect)

        # Legend at top right
        font_leg = QFont("SansSerif", 8, QFont.Weight.Bold)
        painter.setFont(font_leg)

        # CPU Legend
        painter.setPen(QColor(255, 46, 76))
        painter.drawText(QRectF(w - 180, 2, 80, 18), Qt.AlignmentFlag.AlignRight, "━ CPU")

        # GPU Legend
        painter.setPen(QColor(0, 210, 255))
        painter.drawText(QRectF(w - 90, 2, 70, 18), Qt.AlignmentFlag.AlignRight, "━ GPU")

        painter.end()
