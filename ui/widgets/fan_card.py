"""
Fan speed control card widget.
Displays current speed, status, and slider controls for manual fan adjustment.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class FanCard(QWidget):
    speed_changed = pyqtSignal(int)  # Emits new target % (0-100)

    def __init__(self, title: str = "CPU Fan", is_cpu: bool = True, parent=None):
        super().__init__(parent)
        self.title = title
        self.is_cpu = is_cpu
        self.min_pct = 20 if is_cpu else 0
        self.max_pct = 100
        self._interactive = False

        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("FanCard")
        self.setStyleSheet("""
            #FanCard {
                background-color: #1a1c24;
                border-radius: 12px;
                border: 1px solid #2d313d;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 14, 16, 14)

        # Header row: Title + RPM Display
        hdr_layout = QHBoxLayout()
        self.lbl_title = QLabel(self.title)
        self.lbl_title.setStyleSheet("color: #e0e4ee; font-weight: bold; font-size: 14px;")

        self.lbl_rpm = QLabel("0 RPM")
        self.lbl_rpm.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 15px;")

        hdr_layout.addWidget(self.lbl_title)
        hdr_layout.addStretch()
        hdr_layout.addWidget(self.lbl_rpm)
        layout.addLayout(hdr_layout)

        # Status & percentage row
        sub_layout = QHBoxLayout()
        self.lbl_status = QLabel("Auto (Firmware Control)")
        self.lbl_status.setStyleSheet("color: #8b92a5; font-size: 12px;")

        self.lbl_pct = QLabel("50%")
        self.lbl_pct.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")

        sub_layout.addWidget(self.lbl_status)
        sub_layout.addStretch()
        sub_layout.addWidget(self.lbl_pct)
        layout.addLayout(sub_layout)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(self.min_pct, self.max_pct)
        self.slider.setValue(50)
        self.slider.setEnabled(False)  # Disabled until Manual mode

        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #2b2e3b;
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff2e4c, stop:1 #ff6b00);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #ff2e4c;
                width: 18px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #ff2e4c;
                border: 2px solid #ffffff;
            }
            QSlider::handle:horizontal:disabled {
                background: #555a6d;
                border: 1px solid #333644;
            }
        """)

        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)

    def _on_slider_changed(self, val: int):
        self.lbl_pct.setText(f"{val}%")
        if self._interactive:
            self.speed_changed.emit(val)

    def set_speed_pct(self, val: int):
        self._interactive = False
        self.slider.setValue(max(self.min_pct, min(self.max_pct, val)))
        self.lbl_pct.setText(f"{val}%")
        self._interactive = True

    def set_rpm(self, rpm: int):
        self.lbl_rpm.setText(f"{rpm} RPM")
        if rpm > 4500:
            self.lbl_rpm.setStyleSheet("color: #ff2e4c; font-weight: bold; font-size: 15px;")
        elif rpm > 3000:
            self.lbl_rpm.setStyleSheet("color: #ffaa00; font-weight: bold; font-size: 15px;")
        else:
            self.lbl_rpm.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 15px;")

    def set_mode(self, mode_name: str, enable_slider: bool):
        self._interactive = False
        self.slider.setEnabled(enable_slider)
        self.lbl_status.setText(mode_name)
        if enable_slider:
            self.lbl_pct.setText(f"{self.slider.value()}%")
        self._interactive = True
