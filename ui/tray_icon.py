"""
System tray icon for NitroSense Linux.
Provides background monitoring, tooltip thermal info, and quick preset switching.
"""

import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction, QDesktopServices
from PyQt6.QtCore import pyqtSignal, QUrl
from backend.fan_control import FanMode


class NitroTrayIcon(QSystemTrayIcon):
    mode_requested = pyqtSignal(int)
    toggle_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, icon_path: str, parent=None):
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        super().__init__(icon, parent)
        self.setToolTip("Acer Nitro Fan Controller")
        self._setup_menu()
        self.activated.connect(self._on_activated)

    def _setup_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e202a;
                color: #e0e4ee;
                border: 1px solid #333748;
                padding: 6px;
                border-radius: 8px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #ff2e4c;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #333748;
                margin: 4px 0px;
            }
        """)

        self.act_show = QAction("Open NitroSense Dashboard", self)
        self.act_show.triggered.connect(self.toggle_window_requested.emit)
        menu.addAction(self.act_show)
        menu.addSeparator()

        self.act_auto = QAction("⚡ Auto Mode", self)
        self.act_auto.triggered.connect(lambda: self.mode_requested.emit(FanMode.AUTO))
        menu.addAction(self.act_auto)

        self.act_turbo = QAction("🔥 Turbo (Max Fan Boost)", self)
        self.act_turbo.triggered.connect(lambda: self.mode_requested.emit(FanMode.TURBO))
        menu.addAction(self.act_turbo)

        self.act_curve = QAction("📈 Smart Dynamic Curve", self)
        self.act_curve.triggered.connect(lambda: self.mode_requested.emit(FanMode.SMART_CURVE))
        menu.addAction(self.act_curve)

        self.act_manual = QAction("⚙️ Custom Manual", self)
        self.act_manual.triggered.connect(lambda: self.mode_requested.emit(FanMode.MANUAL))
        menu.addAction(self.act_manual)

        menu.addSeparator()
        self.act_repo = QAction("🔗 GitHub: killindodo/nitrosense-linux", self)
        self.act_repo.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/killindodo/nitrosense-linux")))
        menu.addAction(self.act_repo)

        menu.addSeparator()
        self.act_quit = QAction("Quit", self)
        self.act_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(self.act_quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_window_requested.emit()

    def update_tooltip(self, cpu_temp, gpu_temp, cpu_rpm, gpu_rpm, mode_str):
        cpu_t_str = f"{cpu_temp:.0f}°C" if cpu_temp else "N/A"
        gpu_t_str = f"{gpu_temp:.0f}°C" if gpu_temp else "Sleep"
        text = (
            f"NitroSense [{mode_str}]\n"
            f"CPU: {cpu_t_str} | Fans: {cpu_rpm} RPM\n"
            f"GPU: {gpu_t_str} | Fans: {gpu_rpm} RPM"
        )
        self.setToolTip(text)
