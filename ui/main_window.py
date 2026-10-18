"""
Main NitroSense Dashboard Window for Acer Nitro 5 Linux.
Provides real-time thermal monitoring, interactive fan controls,
driver setup integration, and Nitro-themed visuals.
"""

import os
import subprocess
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QCheckBox, QFrame, QMessageBox,
    QScrollArea, QDialog, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon, QFont, QColor

from backend.sensors import SensorMonitor, ThermalSnapshot
from backend.fan_control import FanController, FanMode
from ui.widgets.circular_gauge import CircularGauge
from ui.widgets.thermal_graph import ThermalGraph
from ui.widgets.fan_card import FanCard
from ui.tray_icon import NitroTrayIcon


class NitroSenseWindow(QMainWindow):
    def __init__(self, project_root: str):
        super().__init__()
        self.project_root = project_root
        self.icon_path = os.path.join(project_root, "assets", "icon.png")

        self.monitor = SensorMonitor()
        self.controller = FanController(self.monitor.ec_hwmon)

        self._init_window()
        self._setup_ui()
        self._setup_tray()
        self._setup_timer()

        # Initial poll
        self.update_sensors()

    def _init_window(self):
        self.setWindowTitle(f"NitroSense - {self.monitor.system_model} Fan & Thermal Controller")
        self.resize(880, 720)
        self.setMinimumSize(780, 600)
        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))

        # Main dark theme styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121318;
            }
            QWidget {
                color: #e4e7ee;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
            }
            QFrame#HeaderCard {
                background-color: #181a22;
                border-radius: 12px;
                border: 1px solid #282c3a;
            }
            QFrame#BannerCard {
                background-color: #241e16;
                border-radius: 10px;
                border: 1px solid #ff9800;
            }
            QFrame#SectionCard {
                background-color: #181a22;
                border-radius: 12px;
                border: 1px solid #282c3a;
            }
            QPushButton.mode-btn {
                background-color: #20232e;
                color: #c8cdd8;
                border: 1px solid #33384a;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton.mode-btn:hover {
                background-color: #2a2e3d;
                border-color: #ff2e4c;
                color: #ffffff;
            }
            QPushButton.mode-btn:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff2e4c, stop:1 #e50914);
                color: #ffffff;
                border: 1px solid #ff667d;
            }
            QPushButton.action-btn {
                background-color: #ff2e4c;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton.action-btn:hover {
                background-color: #ff4762;
            }
            QCheckBox {
                spacing: 8px;
                font-size: 13px;
                color: #b0b6c6;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #3d4255;
                background-color: #20232e;
            }
            QCheckBox::indicator:checked {
                background-color: #ff2e4c;
                border-color: #ff2e4c;
            }
            QScrollBar:vertical {
                border: none;
                background: #15171e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #2b2e3b;
                border-radius: 4px;
                min-height: 20px;
            }
        """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # 1. Header Card
        header = QFrame()
        header.setObjectName("HeaderCard")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(18, 12, 18, 12)

        # Title & Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_brand = QLabel("NITROSENSE LINUX")
        lbl_brand.setStyleSheet("color: #ff2e4c; font-size: 18px; font-weight: 900; letter-spacing: 1px;")

        lbl_device = QLabel(f"{self.monitor.system_model} • Thermal & Fan Controller")
        lbl_device.setStyleSheet("color: #8b92a5; font-size: 12px;")
        title_box.addWidget(lbl_brand)
        title_box.addWidget(lbl_device)
        hdr_layout.addLayout(title_box)

        hdr_layout.addStretch()

        # Status badge & Install Driver action
        self.lbl_driver_badge = QLabel("Checking Driver...")
        self.lbl_driver_badge.setStyleSheet("""
            background-color: #252835;
            color: #9aa1b5;
            padding: 6px 14px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        """)
        hdr_layout.addWidget(self.lbl_driver_badge)

        self.btn_install_driver = QPushButton("⚡ Activate Fan Driver")
        self.btn_install_driver.setProperty("class", "action-btn")
        self.btn_install_driver.clicked.connect(self._on_install_driver_clicked)
        hdr_layout.addWidget(self.btn_install_driver)

        main_layout.addWidget(header)

        # 2. Driver Notification Banner (Hidden if loaded)
        self.banner = QFrame()
        self.banner.setObjectName("BannerCard")
        ban_layout = QHBoxLayout(self.banner)
        ban_layout.setContentsMargins(14, 10, 14, 10)
        self.lbl_banner = QLabel(
            "⚠️ Fan Control Driver (acer-nitro-ec) is not loaded. Operating in Thermal Monitoring mode.\n"
            "To enable manual fan speed adjustment and Turbo mode, click 'Activate Driver'."
        )
        self.lbl_banner.setStyleSheet("color: #ffd180; font-size: 12px;")
        ban_layout.addWidget(self.lbl_banner)
        ban_layout.addStretch()

        btn_banner_act = QPushButton("Install / Load Driver")
        btn_banner_act.setStyleSheet("""
            background-color: #ff9800; color: #111; font-weight: bold;
            border-radius: 6px; padding: 6px 14px; font-size: 11px;
        """)
        btn_banner_act.clicked.connect(self._on_install_driver_clicked)
        ban_layout.addWidget(btn_banner_act)
        main_layout.addWidget(self.banner)

        # 3. Circular Gauges (Row of 4)
        gauges_card = QFrame()
        gauges_card.setObjectName("SectionCard")
        gauges_layout = QHBoxLayout(gauges_card)
        gauges_layout.setContentsMargins(10, 14, 10, 14)
        gauges_layout.setSpacing(8)

        self.gauge_cpu_temp = CircularGauge("CPU Temp", "°C", 20, 100)
        self.gauge_gpu_temp = CircularGauge("GPU Temp", "°C", 20, 100)
        self.gauge_cpu_fan = CircularGauge("CPU Fan", "RPM", 0, 6000)
        self.gauge_gpu_fan = CircularGauge("GPU Fan", "RPM", 0, 6000)

        gauges_layout.addWidget(self.gauge_cpu_temp)
        gauges_layout.addWidget(self.gauge_gpu_temp)
        gauges_layout.addWidget(self.gauge_cpu_fan)
        gauges_layout.addWidget(self.gauge_gpu_fan)
        main_layout.addWidget(gauges_card)

        # 4. Mode Selection Bar
        mode_card = QFrame()
        mode_card.setObjectName("SectionCard")
        mode_layout = QHBoxLayout(mode_card)
        mode_layout.setContentsMargins(14, 10, 14, 10)
        mode_layout.setSpacing(12)

        lbl_mode_title = QLabel("FAN MODE:")
        lbl_mode_title.setStyleSheet("color: #8b92a5; font-size: 12px; font-weight: bold;")
        mode_layout.addWidget(lbl_mode_title)

        self.btn_grp_mode = QButtonGroup(self)
        self.btn_auto = QPushButton("⚡ AUTO")
        self.btn_turbo = QPushButton("🔥 MAX / TURBO")
        self.btn_manual = QPushButton("⚙️ CUSTOM")
        self.btn_curve = QPushButton("📈 SMART CURVE")

        for b in [self.btn_auto, self.btn_turbo, self.btn_manual, self.btn_curve]:
            b.setCheckable(True)
            b.setProperty("class", "mode-btn")
            self.btn_grp_mode.addButton(b)
            mode_layout.addWidget(b)

        self.btn_auto.setChecked(True)
        self.btn_auto.clicked.connect(lambda: self.set_mode(FanMode.AUTO))
        self.btn_turbo.clicked.connect(lambda: self.set_mode(FanMode.TURBO))
        self.btn_manual.clicked.connect(lambda: self.set_mode(FanMode.MANUAL))
        self.btn_curve.clicked.connect(lambda: self.set_mode(FanMode.SMART_CURVE))

        mode_layout.addStretch()

        self.chk_sync = QCheckBox("Sync Fan Speeds")
        self.chk_sync.setChecked(True)
        self.chk_sync.toggled.connect(self._on_sync_toggled)
        mode_layout.addWidget(self.chk_sync)

        main_layout.addWidget(mode_card)

        # 5. Fan Speed Cards (Dual Sliders)
        fans_layout = QHBoxLayout()
        fans_layout.setSpacing(14)

        self.card_cpu_fan = FanCard("CPU Cooling Fan", is_cpu=True)
        self.card_gpu_fan = FanCard("GPU Cooling Fan", is_cpu=False)

        self.card_cpu_fan.speed_changed.connect(self._on_cpu_speed_slider)
        self.card_gpu_fan.speed_changed.connect(self._on_gpu_speed_slider)

        fans_layout.addWidget(self.card_cpu_fan)
        fans_layout.addWidget(self.card_gpu_fan)
        main_layout.addLayout(fans_layout)

        # 6. Real-time Thermal History Graph
        graph_card = QFrame()
        graph_card.setObjectName("SectionCard")
        graph_box = QVBoxLayout(graph_card)
        graph_box.setContentsMargins(14, 10, 14, 10)
        graph_box.setSpacing(6)

        hdr_graph = QHBoxLayout()
        lbl_graph = QLabel("REAL-TIME THERMAL DYNAMICS (60 SECONDS)")
        lbl_graph.setStyleSheet("color: #8b92a5; font-size: 11px; font-weight: bold;")
        hdr_graph.addWidget(lbl_graph)
        hdr_graph.addStretch()
        self.lbl_dgpu_info = QLabel("Discrete GPU: Inactive")
        self.lbl_dgpu_info.setStyleSheet("color: #00d2ff; font-size: 11px;")
        hdr_graph.addWidget(self.lbl_dgpu_info)
        graph_box.addLayout(hdr_graph)

        self.graph = ThermalGraph(max_points=60)
        graph_box.addWidget(self.graph)
        main_layout.addWidget(graph_card)

        # 7. Watermark & Repository Footer
        footer = QFrame()
        footer.setObjectName("FooterCard")
        footer.setStyleSheet("""
            #FooterCard {
                background-color: #161820;
                border-radius: 8px;
                border: 1px solid #242836;
            }
        """)
        ftr_layout = QHBoxLayout(footer)
        ftr_layout.setContentsMargins(14, 6, 14, 6)

        lbl_author = QLabel("⚡ NitroSense Linux • Fan & Thermal Controller")
        lbl_author.setStyleSheet("color: #9aa1b5; font-size: 11px;")

        lbl_repo = QLabel("<a href='https://github.com/killindodo/nitrosense-linux' style='color: #00d2ff; text-decoration: none;'>🔗 GitHub Repository</a>")
        lbl_repo.setOpenExternalLinks(True)
        lbl_repo.setStyleSheet("font-size: 11px;")

        lbl_version = QLabel("NitroSense Linux v1.1.0")
        lbl_version.setStyleSheet("color: #63697a; font-size: 11px;")

        ftr_layout.addWidget(lbl_author)
        ftr_layout.addSpacing(16)
        ftr_layout.addWidget(lbl_repo)
        ftr_layout.addStretch()
        ftr_layout.addWidget(lbl_version)

        main_layout.addWidget(footer)

    def _setup_tray(self):
        self.tray = NitroTrayIcon(self.icon_path, self.monitor.system_model, self)
        self.tray.mode_requested.connect(self.set_mode)
        self.tray.speed_changed.connect(self._on_tray_speed_changed)
        self.tray.sync_toggled.connect(self._on_tray_sync_toggled)
        self.tray.toggle_window_requested.connect(self.toggle_visibility)
        self.tray.quit_requested.connect(self.close)
        self.tray.show()

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_sensors)
        self.timer.start(1000)  # 1-second update interval

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def set_mode(self, mode: int):
        self.controller.set_mode(mode)
        self._update_mode_buttons(mode)
        self.tray.set_mode(mode)

    def _update_mode_buttons(self, mode: int):
        self.btn_auto.setChecked(mode == FanMode.AUTO)
        self.btn_turbo.setChecked(mode == FanMode.TURBO)
        self.btn_manual.setChecked(mode == FanMode.MANUAL)
        self.btn_curve.setChecked(mode == FanMode.SMART_CURVE)

        can_slide = (mode == FanMode.MANUAL)
        mode_names = {
            FanMode.AUTO: "Auto (Firmware Control)",
            FanMode.TURBO: "Turbo (Max 100% Boost)",
            FanMode.MANUAL: "Manual Duty Cycle",
            FanMode.SMART_CURVE: "Smart Dynamic Curve",
        }
        name = mode_names.get(mode, "Unknown")
        self.card_cpu_fan.set_mode(name, can_slide)
        self.card_gpu_fan.set_mode(name, can_slide)

    def _on_sync_toggled(self, checked: bool):
        self.controller.synced = checked
        self.tray.set_sync(checked)
        if checked:
            # Sync GPU slider to CPU slider
            val = self.card_cpu_fan.slider.value()
            self.card_gpu_fan.set_speed_pct(val)
            self.controller.apply_speeds(val, val)
            self.tray.set_slider_values(val, val)

    def _on_cpu_speed_slider(self, val: int):
        gpu_val = val if self.chk_sync.isChecked() else self.card_gpu_fan.slider.value()
        if self.chk_sync.isChecked():
            self.card_gpu_fan.set_speed_pct(val)
        self.controller.apply_speeds(val, gpu_val)
        self.tray.set_slider_values(val, gpu_val)

    def _on_gpu_speed_slider(self, val: int):
        if self.chk_sync.isChecked():
            self.card_cpu_fan.set_speed_pct(val)
            self.controller.apply_speeds(val, val)
            self.tray.set_slider_values(val, val)
        else:
            cpu_val = self.card_cpu_fan.slider.value()
            self.controller.apply_speeds(cpu_val, val)
            self.tray.set_slider_values(cpu_val, val)

    def _on_tray_speed_changed(self, cpu_val: int, gpu_val: int):
        self.card_cpu_fan.set_speed_pct(cpu_val)
        self.card_gpu_fan.set_speed_pct(gpu_val)
        self.controller.apply_speeds(cpu_val, gpu_val)

    def _on_tray_sync_toggled(self, checked: bool):
        self.chk_sync.setChecked(checked)
        self.controller.synced = checked

    @pyqtSlot()
    def update_sensors(self):
        snap: ThermalSnapshot = self.monitor.poll()
        self.controller.set_hwmon_path(snap.ec_path)

        # Update Driver Status Badge & Banner
        if snap.ec_available:
            if snap.ec_writable:
                self.lbl_driver_badge.setText("✓ EC Driver: Ready")
                self.lbl_driver_badge.setStyleSheet("""
                    background-color: #1b382b; color: #00e676;
                    padding: 6px 14px; border-radius: 12px; font-size: 12px; font-weight: bold;
                """)
                self.btn_install_driver.setVisible(False)
                self.banner.setVisible(False)
            else:
                self.lbl_driver_badge.setText("⚠️ EC Driver: Read-Only")
                self.lbl_driver_badge.setStyleSheet("""
                    background-color: #3d2f16; color: #ffb300;
                    padding: 6px 14px; border-radius: 12px; font-size: 12px; font-weight: bold;
                """)
                self.btn_install_driver.setText("Fix Permissions")
                self.btn_install_driver.setVisible(True)
                self.banner.setVisible(True)
                self.lbl_banner.setText("⚠️ Driver loaded but requires udev write permissions to adjust fan speeds.")
        else:
            self.lbl_driver_badge.setText("❌ EC Driver: Not Loaded")
            self.lbl_driver_badge.setStyleSheet("""
                background-color: #351c24; color: #ff5252;
                padding: 6px 14px; border-radius: 12px; font-size: 12px; font-weight: bold;
            """)
            self.btn_install_driver.setText("⚡ Activate Driver")
            self.btn_install_driver.setVisible(True)
            self.banner.setVisible(True)

        # Update CPU Gauge
        if snap.cpu_temp is not None:
            self.gauge_cpu_temp.set_value(snap.cpu_temp, snap.cpu_label)
        else:
            self.gauge_cpu_temp.set_value(0, "Offline")

        # Update GPU Gauge
        if snap.dgpu_temp is not None and snap.dgpu_active:
            sub = ""
            if snap.dgpu_power_w is not None:
                sub = f"{snap.dgpu_power_w:.1f}W"
            if snap.dgpu_sclk_mhz is not None:
                sub += f" • {snap.dgpu_sclk_mhz}MHz"
            self.gauge_gpu_temp.set_value(snap.dgpu_temp, sub or snap.dgpu_name)
            self.lbl_dgpu_info.setText(f"Discrete GPU: {snap.dgpu_temp:.1f}°C ({sub or snap.dgpu_name})")
        elif snap.igpu_temp is not None:
            self.gauge_gpu_temp.set_value(snap.igpu_temp, snap.igpu_name)
            self.lbl_dgpu_info.setText(f"Discrete GPU: Standby • {snap.igpu_name} Active")
        else:
            self.gauge_gpu_temp.set_value(0, "Sleeping")
            self.lbl_dgpu_info.setText("Discrete GPU: Sleeping")

        # Update Fan Gauges & Cards
        self.gauge_cpu_fan.set_value(snap.cpu_fan_rpm, f"{snap.cpu_fan_pct}%")
        self.gauge_gpu_fan.set_value(snap.gpu_fan_rpm, f"{snap.gpu_fan_pct}%")

        self.card_cpu_fan.set_rpm(snap.cpu_fan_rpm)
        self.card_gpu_fan.set_rpm(snap.gpu_fan_rpm)

        # Update graph
        best_gpu_temp = snap.dgpu_temp if (snap.dgpu_temp and snap.dgpu_active) else snap.igpu_temp
        self.graph.add_data_point(snap.cpu_temp, best_gpu_temp)

        # Execute curve & safety ticks
        self.controller.tick_safety_and_curve(snap.cpu_temp, best_gpu_temp)

        # Update Tray Tooltip and Mini Control Dropdown
        self.tray.update_snapshot(snap, self.controller.active_mode)

    def _on_install_driver_clicked(self):
        script = os.path.join(self.project_root, "scripts", "install_driver.sh")
        msg = QMessageBox(self)
        msg.setWindowTitle("Activate Fan Control Driver")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("Would you like to install and activate the Acer Nitro EC fan driver?")
        msg.setInformativeText(
            f"This will compile the acer-nitro-ec kernel module for your {self.monitor.system_model}, "
            "install it with DKMS for automatic kernel updates, and configure udev rules "
            "so you can control fan speeds without entering a password.\n\n"
            "An authorization prompt (pkexec) will appear asking for your password."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        btn_terminal = msg.addButton("Run in Terminal", QMessageBox.ButtonRole.ActionRole)

        ret = msg.exec()
        if ret == QMessageBox.StandardButton.Yes:
            try:
                subprocess.Popen(["pkexec", script])
                QMessageBox.information(
                    self,
                    "Driver Activation Started",
                    "The driver installation has been initiated. Once authorized, "
                    "NitroSense will automatically detect the driver within a few seconds."
                )
            except Exception as e:
                QMessageBox.critical(self, "Execution Failed", f"Could not launch pkexec:\n{e}")
        elif msg.clickedButton() == btn_terminal:
            dialog = QDialog(self)
            dialog.setWindowTitle("Terminal Installation Command")
            d_layout = QVBoxLayout(dialog)
            lbl = QLabel("Run this command in your terminal:")
            d_layout.addWidget(lbl)
            txt = QTextEdit()
            txt.setPlainText(f"sudo {script}")
            txt.setReadOnly(True)
            txt.setMaximumHeight(60)
            d_layout.addWidget(txt)
            btn_close = QPushButton("Done")
            btn_close.clicked.connect(dialog.accept)
            d_layout.addWidget(btn_close)
            dialog.exec()

    def closeEvent(self, event):
        # Reset fans to safe Auto mode on shutdown
        self.controller.safety_reset()
        event.accept()
