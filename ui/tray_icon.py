"""
System tray icon for NitroSense Linux.
Provides background status bar monitoring, quick tooltip readouts,
right-click preset switching, and an on-click interactive Mini Control Dropdown.
"""

import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction, QDesktopServices
from PyQt6.QtCore import pyqtSignal, QUrl

from backend.fan_control import FanMode
from backend.sensors import ThermalSnapshot
from ui.mini_control import MiniControlDropdown


class NitroTrayIcon(QSystemTrayIcon):
    mode_requested = pyqtSignal(int)
    speed_changed = pyqtSignal(int, int)
    sync_toggled = pyqtSignal(bool)
    toggle_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, icon_path: str, system_model: str = "Acer Nitro", parent=None):
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        super().__init__(icon, parent)
        self.setToolTip("NitroSense Fan & Thermal Controller")

        # Initialize the Mini Control Dropdown
        self.mini_control = MiniControlDropdown(system_model=system_model)
        self.mini_control.mode_requested.connect(self.mode_requested.emit)
        self.mini_control.speed_changed.connect(self.speed_changed.emit)
        self.mini_control.sync_toggled.connect(self.sync_toggled.emit)
        self.mini_control.open_dashboard_requested.connect(self.toggle_window_requested.emit)
        self.mini_control.quit_requested.connect(self.quit_requested.emit)

        self._setup_menu()
        self.activated.connect(self._on_activated)

    def _setup_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1c26;
                color: #e0e4ee;
                border: 1px solid #2d3246;
                padding: 6px;
                border-radius: 8px;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 22px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #ff2e4c;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2b2f42;
                margin: 4px 2px;
            }
        """)

        # Quick Control Dropdown Action
        self.act_mini = QAction("🎛️ Quick Control Dropdown", self)
        self.act_mini.triggered.connect(self.toggle_mini_control)
        menu.addAction(self.act_mini)

        self.act_show = QAction("🖥️ Open Full Dashboard", self)
        self.act_show.triggered.connect(self.toggle_window_requested.emit)
        menu.addAction(self.act_show)

        menu.addSeparator()

        self.act_auto = QAction("⚡ Auto Profile", self)
        self.act_auto.triggered.connect(lambda: self.mode_requested.emit(FanMode.AUTO))
        menu.addAction(self.act_auto)

        self.act_turbo = QAction("🔥 Turbo (Max Fan Boost)", self)
        self.act_turbo.triggered.connect(lambda: self.mode_requested.emit(FanMode.TURBO))
        menu.addAction(self.act_turbo)

        self.act_curve = QAction("📈 Smart Dynamic Curve", self)
        self.act_curve.triggered.connect(lambda: self.mode_requested.emit(FanMode.SMART_CURVE))
        menu.addAction(self.act_curve)

        self.act_manual = QAction("⚙️ Custom Manual Speed", self)
        self.act_manual.triggered.connect(lambda: self.mode_requested.emit(FanMode.MANUAL))
        menu.addAction(self.act_manual)

        menu.addSeparator()
        self.act_repo = QAction("🔗 GitHub: killindodo/nitrosense-linux", self)
        self.act_repo.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/killindodo/nitrosense-linux"))
        )
        menu.addAction(self.act_repo)

        menu.addSeparator()
        self.act_quit = QAction("Quit NitroSense", self)
        self.act_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(self.act_quit)

        self.setContextMenu(menu)

    def toggle_mini_control(self):
        """Toggles the visibility of the Mini Control Dropdown."""
        if self.mini_control.isVisible():
            self.mini_control.hide()
        else:
            self.mini_control.show_at_tray(self)

    def _on_activated(self, reason):
        # Click (Trigger) opens the Mini Control Dropdown
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_mini_control()
        # Double Click opens the full main dashboard window
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window_requested.emit()

    def update_snapshot(self, snap: ThermalSnapshot, mode: int):
        """Updates both tooltip and the open Mini Control Dropdown."""
        # 1. Update Mini Control Dropdown
        self.mini_control.update_snapshot(snap, mode)

        # 2. Update Tooltip
        cpu_t_str = f"{snap.cpu_temp:.0f}°C" if snap.cpu_temp else "N/A"
        active_gpu_temp = snap.dgpu_temp if (snap.dgpu_temp and snap.dgpu_active) else snap.igpu_temp
        gpu_t_str = f"{active_gpu_temp:.0f}°C" if active_gpu_temp else "Standby"
        mode_str = ["Turbo", "Manual", "Auto", "SmartCurve"][mode]

        tooltip_text = (
            f"{snap.system_model} [{mode_str}]\n"
            f"CPU: {cpu_t_str} | Fans: {snap.cpu_fan_rpm} RPM\n"
            f"GPU: {gpu_t_str} | Fans: {snap.gpu_fan_rpm} RPM"
        )
        self.setToolTip(tooltip_text)

    def set_mode(self, mode: int):
        self.mini_control.set_mode(mode)

    def set_sync(self, synced: bool):
        self.mini_control.set_sync(synced)

    def set_slider_values(self, cpu_val: int, gpu_val: int):
        self.mini_control.set_slider_values(cpu_val, gpu_val)
