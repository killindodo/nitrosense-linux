"""
Mini Control Dropdown Widget for NitroSense Linux.
Provides a sleek, modern popup dropdown from the top status bar / tray widget
displaying real-time CPU & GPU temperatures, fan speeds, mode toggles,
and interactive fan sliders.
"""

import os
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QCheckBox, QFrame, QButtonGroup, QProgressBar,
    QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QColor, QFont, QCursor, QGuiApplication

from backend.fan_control import FanMode
from backend.sensors import ThermalSnapshot


class MiniControlDropdown(QWidget):
    """
    Compact popup dropdown positioned beneath (or adjacent to) the top status bar
    tray icon. Provides quick thermal monitoring and full fan control.
    """
    mode_requested = pyqtSignal(int)
    speed_changed = pyqtSignal(int, int)  # cpu_pct, gpu_pct
    sync_toggled = pyqtSignal(bool)
    open_dashboard_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, system_model: str = "Acer Nitro", parent=None):
        super().__init__(parent, flags=Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.system_model = system_model
        self.synced = True
        self.active_mode = FanMode.AUTO
        self._is_updating = False

        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(340)

        # Outer root layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)

        # Main Card Frame
        self.card = QFrame(self)
        self.card.setObjectName("MiniCard")
        self.card.setStyleSheet("""
            QFrame#MiniCard {
                background-color: #14161f;
                border: 1px solid #282c3c;
                border-radius: 14px;
            }
            QLabel {
                color: #e4e7ee;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
            }
            QFrame#MetricBox {
                background-color: #1a1c26;
                border: 1px solid #282b3a;
                border-radius: 10px;
                padding: 6px;
            }
            QPushButton.mini-mode-btn {
                background-color: #1e212c;
                color: #b0b6c6;
                border: 1px solid #2d3244;
                border-radius: 6px;
                padding: 6px 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton.mini-mode-btn:hover {
                background-color: #272b3a;
                border-color: #ff2e4c;
                color: #ffffff;
            }
            QPushButton.mini-mode-btn:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff2e4c, stop:1 #e50914);
                color: #ffffff;
                border: 1px solid #ff667d;
            }
            QSlider::groove:horizontal {
                height: 5px;
                background: #252836;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff2e4c, stop:1 #ff667d);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #ff2e4c;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #ff4762;
            }
            QCheckBox {
                font-size: 11px;
                color: #9aa1b5;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #3d4255;
                background-color: #1e212c;
            }
            QCheckBox::indicator:checked {
                background-color: #ff2e4c;
                border-color: #ff2e4c;
            }
            QProgressBar {
                background-color: #1e212d;
                border-radius: 3px;
                height: 4px;
                text-align: right;
            }
            QProgressBar::chunk {
                background-color: #ff2e4c;
                border-radius: 3px;
            }
            QPushButton.action-link {
                background: transparent;
                color: #00d2ff;
                border: none;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton.action-link:hover {
                background-color: #1b2838;
                color: #66e0ff;
            }
            QPushButton.quit-link {
                background: transparent;
                color: #8b92a5;
                border: none;
                font-size: 11px;
                padding: 4px 6px;
                border-radius: 4px;
            }
            QPushButton.quit-link:hover {
                background-color: #2a1f24;
                color: #ff5252;
            }
        """)

        # Drop shadow for a floating popover feel
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. Header: Status badge, Title & Expand/Close buttons
        # -------------------------------------------------------------
        hdr_layout = QHBoxLayout()
        hdr_layout.setSpacing(6)

        # Glowing Nitro Indicator Dot
        self.lbl_dot = QLabel("●")
        self.lbl_dot.setStyleSheet("color: #ff2e4c; font-size: 14px;")
        hdr_layout.addWidget(self.lbl_dot)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(0)
        self.lbl_title = QLabel("NITROSENSE")
        self.lbl_title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 900; letter-spacing: 0.5px;")
        self.lbl_sub = QLabel(self.system_model)
        self.lbl_sub.setStyleSheet("color: #8a90a2; font-size: 10px;")
        title_vbox.addWidget(self.lbl_title)
        title_vbox.addWidget(self.lbl_sub)
        hdr_layout.addLayout(title_vbox)

        hdr_layout.addStretch()

        # Dashboard Expand Button
        self.btn_open_dash = QPushButton("🗗 Dashboard")
        self.btn_open_dash.setProperty("class", "action-link")
        self.btn_open_dash.setToolTip("Open Full NitroSense Dashboard")
        self.btn_open_dash.clicked.connect(self._on_dashboard_clicked)
        hdr_layout.addWidget(self.btn_open_dash)

        # Close button
        self.btn_close = QPushButton("✕")
        self.btn_close.setProperty("class", "quit-link")
        self.btn_close.setToolTip("Close Dropdown")
        self.btn_close.clicked.connect(self.hide)
        hdr_layout.addWidget(self.btn_close)

        card_layout.addLayout(hdr_layout)

        # Separator line
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #242735;")
        card_layout.addWidget(sep)

        # -------------------------------------------------------------
        # 2. Metrics: Dual Cards for CPU & GPU (Temp + RPM + Meter)
        # -------------------------------------------------------------
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(8)

        # CPU Metric Box
        self.box_cpu = QFrame()
        self.box_cpu.setObjectName("MetricBox")
        cpu_layout = QVBoxLayout(self.box_cpu)
        cpu_layout.setContentsMargins(8, 6, 8, 6)
        cpu_layout.setSpacing(3)

        lbl_cpu_hdr = QLabel("CPU COOLING")
        lbl_cpu_hdr.setStyleSheet("color: #00d2ff; font-size: 9px; font-weight: bold; letter-spacing: 0.5px;")
        cpu_layout.addWidget(lbl_cpu_hdr)

        self.lbl_cpu_temp = QLabel("-- °C")
        self.lbl_cpu_temp.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        cpu_layout.addWidget(self.lbl_cpu_temp)

        self.lbl_cpu_fan = QLabel("0 RPM (0%)")
        self.lbl_cpu_fan.setStyleSheet("color: #8b92a5; font-size: 10px;")
        cpu_layout.addWidget(self.lbl_cpu_fan)

        self.bar_cpu_fan = QProgressBar()
        self.bar_cpu_fan.setRange(0, 100)
        self.bar_cpu_fan.setValue(0)
        self.bar_cpu_fan.setTextVisible(False)
        self.bar_cpu_fan.setFixedHeight(4)
        cpu_layout.addWidget(self.bar_cpu_fan)

        metrics_layout.addWidget(self.box_cpu)

        # GPU Metric Box
        self.box_gpu = QFrame()
        self.box_gpu.setObjectName("MetricBox")
        gpu_layout = QVBoxLayout(self.box_gpu)
        gpu_layout.setContentsMargins(8, 6, 8, 6)
        gpu_layout.setSpacing(3)

        lbl_gpu_hdr = QLabel("GPU COOLING")
        lbl_gpu_hdr.setStyleSheet("color: #ff2e4c; font-size: 9px; font-weight: bold; letter-spacing: 0.5px;")
        gpu_layout.addWidget(lbl_gpu_hdr)

        self.lbl_gpu_temp = QLabel("-- °C")
        self.lbl_gpu_temp.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        gpu_layout.addWidget(self.lbl_gpu_temp)

        self.lbl_gpu_fan = QLabel("0 RPM (0%)")
        self.lbl_gpu_fan.setStyleSheet("color: #8b92a5; font-size: 10px;")
        gpu_layout.addWidget(self.lbl_gpu_fan)

        self.bar_gpu_fan = QProgressBar()
        self.bar_gpu_fan.setRange(0, 100)
        self.bar_gpu_fan.setValue(0)
        self.bar_gpu_fan.setTextVisible(False)
        self.bar_gpu_fan.setFixedHeight(4)
        gpu_layout.addWidget(self.bar_gpu_fan)

        metrics_layout.addWidget(self.box_gpu)
        card_layout.addLayout(metrics_layout)

        # -------------------------------------------------------------
        # 3. Fan Mode Buttons (Auto, Turbo, Custom, Curve)
        # -------------------------------------------------------------
        lbl_modes_title = QLabel("FAN PROFILE")
        lbl_modes_title.setStyleSheet("color: #72788e; font-size: 9px; font-weight: bold; letter-spacing: 0.5px;")
        card_layout.addWidget(lbl_modes_title)

        modes_layout = QHBoxLayout()
        modes_layout.setSpacing(6)

        self.btn_grp_mode = QButtonGroup(self)
        self.btn_auto = QPushButton("⚡ Auto")
        self.btn_turbo = QPushButton("🔥 Turbo")
        self.btn_manual = QPushButton("⚙️ Custom")
        self.btn_curve = QPushButton("📈 Curve")

        for idx, btn in enumerate([self.btn_auto, self.btn_turbo, self.btn_manual, self.btn_curve]):
            btn.setCheckable(True)
            btn.setProperty("class", "mini-mode-btn")
            self.btn_grp_mode.addButton(btn)
            modes_layout.addWidget(btn)

        self.btn_auto.setChecked(True)
        self.btn_auto.clicked.connect(lambda: self._on_mode_button(FanMode.AUTO))
        self.btn_turbo.clicked.connect(lambda: self._on_mode_button(FanMode.TURBO))
        self.btn_manual.clicked.connect(lambda: self._on_mode_button(FanMode.MANUAL))
        self.btn_curve.clicked.connect(lambda: self._on_mode_button(FanMode.SMART_CURVE))

        card_layout.addLayout(modes_layout)

        # -------------------------------------------------------------
        # 4. Interactive Fan Sliders & Sync Toggle
        # -------------------------------------------------------------
        ctrl_hdr = QHBoxLayout()
        lbl_ctrl_title = QLabel("SPEED ADJUSTMENT")
        lbl_ctrl_title.setStyleSheet("color: #72788e; font-size: 9px; font-weight: bold; letter-spacing: 0.5px;")
        ctrl_hdr.addWidget(lbl_ctrl_title)
        ctrl_hdr.addStretch()

        self.chk_sync = QCheckBox("Sync Fans")
        self.chk_sync.setChecked(True)
        self.chk_sync.toggled.connect(self._on_sync_toggled)
        ctrl_hdr.addWidget(self.chk_sync)
        card_layout.addLayout(ctrl_hdr)

        # CPU Slider Row
        cpu_slider_row = QHBoxLayout()
        cpu_slider_row.setSpacing(8)
        lbl_cpu_s = QLabel("CPU")
        lbl_cpu_s.setStyleSheet("color: #9aa1b5; font-size: 10px; font-weight: bold; width: 28px;")
        self.slider_cpu = QSlider(Qt.Orientation.Horizontal)
        self.slider_cpu.setRange(20, 100)
        self.slider_cpu.setValue(50)
        self.lbl_cpu_pct = QLabel("50%")
        self.lbl_cpu_pct.setStyleSheet("color: #e4e7ee; font-size: 11px; width: 32px;")
        self.slider_cpu.valueChanged.connect(self._on_cpu_slider_changed)

        cpu_slider_row.addWidget(lbl_cpu_s)
        cpu_slider_row.addWidget(self.slider_cpu)
        cpu_slider_row.addWidget(self.lbl_cpu_pct)
        card_layout.addLayout(cpu_slider_row)

        # GPU Slider Row
        gpu_slider_row = QHBoxLayout()
        gpu_slider_row.setSpacing(8)
        lbl_gpu_s = QLabel("GPU")
        lbl_gpu_s.setStyleSheet("color: #9aa1b5; font-size: 10px; font-weight: bold; width: 28px;")
        self.slider_gpu = QSlider(Qt.Orientation.Horizontal)
        self.slider_gpu.setRange(0, 100)
        self.slider_gpu.setValue(50)
        self.lbl_gpu_pct = QLabel("50%")
        self.lbl_gpu_pct.setStyleSheet("color: #e4e7ee; font-size: 11px; width: 32px;")
        self.slider_gpu.valueChanged.connect(self._on_gpu_slider_changed)

        gpu_slider_row.addWidget(lbl_gpu_s)
        gpu_slider_row.addWidget(self.slider_gpu)
        gpu_slider_row.addWidget(self.lbl_gpu_pct)
        card_layout.addLayout(gpu_slider_row)

        # -------------------------------------------------------------
        # 5. Footer: Driver Status & Quit Action
        # -------------------------------------------------------------
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background-color: #242735;")
        card_layout.addWidget(sep2)

        ftr_layout = QHBoxLayout()
        ftr_layout.setContentsMargins(0, 2, 0, 0)

        self.lbl_driver_status = QLabel("● Driver: Ready")
        self.lbl_driver_status.setStyleSheet("color: #00e676; font-size: 10px; font-weight: bold;")
        ftr_layout.addWidget(self.lbl_driver_status)

        ftr_layout.addStretch()

        btn_quit = QPushButton("Quit App")
        btn_quit.setProperty("class", "quit-link")
        btn_quit.setToolTip("Safely restore auto fans and quit NitroSense")
        btn_quit.clicked.connect(self.quit_requested.emit)
        ftr_layout.addWidget(btn_quit)

        card_layout.addLayout(ftr_layout)
        root_layout.addWidget(self.card)

    def _on_dashboard_clicked(self):
        self.hide()
        self.open_dashboard_requested.emit()

    def _on_mode_button(self, mode: int):
        self.active_mode = mode
        self._update_slider_states(mode)
        self.mode_requested.emit(mode)

    def _on_sync_toggled(self, checked: bool):
        self.synced = checked
        if checked:
            val = self.slider_cpu.value()
            self.slider_gpu.setValue(val)
            self.speed_changed.emit(val, val)
        self.sync_toggled.emit(checked)

    def _on_cpu_slider_changed(self, val: int):
        self.lbl_cpu_pct.setText(f"{val}%")
        if self._is_updating:
            return
        if self.synced:
            self._is_updating = True
            self.slider_gpu.setValue(val)
            self.lbl_gpu_pct.setText(f"{val}%")
            self._is_updating = False
            self.speed_changed.emit(val, val)
        else:
            self.speed_changed.emit(val, self.slider_gpu.value())

        # If user drags slider while not in manual mode, switch to manual automatically
        if self.active_mode != FanMode.MANUAL:
            self.btn_manual.setChecked(True)
            self.active_mode = FanMode.MANUAL
            self.mode_requested.emit(FanMode.MANUAL)

    def _on_gpu_slider_changed(self, val: int):
        self.lbl_gpu_pct.setText(f"{val}%")
        if self._is_updating:
            return
        if self.synced:
            self._is_updating = True
            self.slider_cpu.setValue(val)
            self.lbl_cpu_pct.setText(f"{val}%")
            self._is_updating = False
            self.speed_changed.emit(val, val)
        else:
            self.speed_changed.emit(self.slider_cpu.value(), val)

        if self.active_mode != FanMode.MANUAL:
            self.btn_manual.setChecked(True)
            self.active_mode = FanMode.MANUAL
            self.mode_requested.emit(FanMode.MANUAL)

    def _update_slider_states(self, mode: int):
        is_manual = (mode == FanMode.MANUAL)
        self.slider_cpu.setEnabled(is_manual)
        self.slider_gpu.setEnabled(is_manual)
        opacity = "1.0" if is_manual else "0.4"
        self.slider_cpu.setStyleSheet(f"opacity: {opacity};")
        self.slider_gpu.setStyleSheet(f"opacity: {opacity};")

    def set_mode(self, mode: int):
        self.active_mode = mode
        self.btn_auto.setChecked(mode == FanMode.AUTO)
        self.btn_turbo.setChecked(mode == FanMode.TURBO)
        self.btn_manual.setChecked(mode == FanMode.MANUAL)
        self.btn_curve.setChecked(mode == FanMode.SMART_CURVE)
        self._update_slider_states(mode)

    def set_sync(self, synced: bool):
        self.synced = synced
        self.chk_sync.setChecked(synced)

    def set_slider_values(self, cpu_val: int, gpu_val: int):
        self._is_updating = True
        self.slider_cpu.setValue(cpu_val)
        self.slider_gpu.setValue(gpu_val)
        self.lbl_cpu_pct.setText(f"{cpu_val}%")
        self.lbl_gpu_pct.setText(f"{gpu_val}%")
        self._is_updating = False

    def update_snapshot(self, snap: ThermalSnapshot, mode: int):
        """Called every second by the monitor timer to refresh live readouts."""
        # 1. Update CPU readout
        if snap.cpu_temp is not None:
            self.lbl_cpu_temp.setText(f"{snap.cpu_temp:.0f}°C")
            if snap.cpu_temp >= 80:
                self.lbl_cpu_temp.setStyleSheet("color: #ff334b; font-size: 18px; font-weight: bold;")
            elif snap.cpu_temp >= 65:
                self.lbl_cpu_temp.setStyleSheet("color: #ffb300; font-size: 18px; font-weight: bold;")
            else:
                self.lbl_cpu_temp.setStyleSheet("color: #00e676; font-size: 18px; font-weight: bold;")
        else:
            self.lbl_cpu_temp.setText("N/A")
            self.lbl_cpu_temp.setStyleSheet("color: #8b92a5; font-size: 18px; font-weight: bold;")

        self.lbl_cpu_fan.setText(f"{snap.cpu_fan_rpm} RPM ({snap.cpu_fan_pct}%)")
        self.bar_cpu_fan.setValue(snap.cpu_fan_pct)

        # 2. Update GPU readout
        active_gpu_temp = snap.dgpu_temp if (snap.dgpu_temp and snap.dgpu_active) else snap.igpu_temp
        if active_gpu_temp is not None:
            self.lbl_gpu_temp.setText(f"{active_gpu_temp:.0f}°C")
            if active_gpu_temp >= 80:
                self.lbl_gpu_temp.setStyleSheet("color: #ff334b; font-size: 18px; font-weight: bold;")
            elif active_gpu_temp >= 65:
                self.lbl_gpu_temp.setStyleSheet("color: #ffb300; font-size: 18px; font-weight: bold;")
            else:
                self.lbl_gpu_temp.setStyleSheet("color: #00e676; font-size: 18px; font-weight: bold;")
        elif snap.dgpu_temp is not None:
            self.lbl_gpu_temp.setText(f"{snap.dgpu_temp:.0f}°C")
            self.lbl_gpu_temp.setStyleSheet("color: #8b92a5; font-size: 18px; font-weight: bold;")
        else:
            self.lbl_gpu_temp.setText("Standby")
            self.lbl_gpu_temp.setStyleSheet("color: #8b92a5; font-size: 18px; font-weight: bold;")

        self.lbl_gpu_fan.setText(f"{snap.gpu_fan_rpm} RPM ({snap.gpu_fan_pct}%)")
        self.bar_gpu_fan.setValue(snap.gpu_fan_pct)

        # 3. Update Driver Status Badge
        if snap.ec_available:
            if snap.ec_writable:
                self.lbl_driver_status.setText("● Driver: Active & Ready")
                self.lbl_driver_status.setStyleSheet("color: #00e676; font-size: 10px; font-weight: bold;")
            else:
                self.lbl_driver_status.setText("⚠️ Driver: Read-Only (Check udev)")
                self.lbl_driver_status.setStyleSheet("color: #ffb300; font-size: 10px; font-weight: bold;")
        else:
            self.lbl_driver_status.setText("❌ Driver: Not Loaded")
            self.lbl_driver_status.setStyleSheet("color: #ff5252; font-size: 10px; font-weight: bold;")

        # Keep mode buttons synced if mode changed externally
        if self.active_mode != mode:
            self.set_mode(mode)

    def show_at_tray(self, tray_icon):
        """
        Positions the mini control dropdown immediately beneath (for top status bar)
        or above (for bottom taskbar) the tray icon, clamped to screen boundaries.
        """
        anchor = QCursor.pos()
        tray_geom = tray_icon.geometry()
        if tray_geom.isValid() and not tray_geom.isNull() and tray_geom.width() > 0:
            anchor = tray_geom.center()

        screen = QGuiApplication.screenAt(anchor) or QApplication.primaryScreen()
        avail = screen.availableGeometry()

        self.adjustSize()
        w = self.width()
        h = self.height()

        # Center horizontally on anchor, clamped within screen margins
        x = anchor.x() - w // 2
        x = max(avail.left() + 8, min(avail.right() - w - 8, x))

        # Check if status bar is at the top or bottom of the screen
        if anchor.y() < avail.center().y():
            # Top status bar: position dropdown below tray icon
            y = (tray_geom.bottom() + 6) if (tray_geom.isValid() and tray_geom.width() > 0) else (anchor.y() + 8)
        else:
            # Bottom panel: position dropdown above tray icon
            y = (tray_geom.top() - h - 6) if (tray_geom.isValid() and tray_geom.width() > 0) else (anchor.y() - h - 8)

        # Clamp vertically
        y = max(avail.top() + 8, min(avail.bottom() - h - 8, y))

        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
