#!/usr/bin/env python3
"""
NitroSense Linux - Advanced Fan & Thermal Controller for Acer Nitro 5 AN515-42
Developer: killindodo (https://github.com/killindodo)
Repository: https://github.com/killindodo/nitrosense-linux
"""

__author__ = "killindodo"
__version__ = "1.0.0"
__github__ = "https://github.com/killindodo/nitrosense-linux"

import sys
import os
import signal
import argparse

# Ensure project directory is in python path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer
from ui.main_window import NitroSenseWindow


def main():
    parser = argparse.ArgumentParser(description="Acer Nitro 5 Fan and Thermal Controller")
    parser.add_argument("--tray", action="store_true", help="Start minimized to the system tray")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("NitroSense Linux")
    app.setApplicationDisplayName("NitroSense")
    app.setDesktopFileName("nitrosense")

    icon_path = os.path.join(PROJECT_DIR, "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = NitroSenseWindow(PROJECT_DIR)

    if not args.tray:
        window.show()
    else:
        window.hide()

    # Handle Ctrl+C in terminal
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    sig_timer = QTimer()
    sig_timer.start(500)
    sig_timer.timeout.connect(lambda: None)  # Allows Python interpreter to catch signals

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
