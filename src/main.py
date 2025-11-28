#!/usr/bin/env python3
"""
4Charm - Advanced 4chan Media Downloader
A high-performance GUI application for bulk downloading media from 4chan threads and boards.
Version: 5.2.0
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from src.utils.logging_setup import setup_logging
from src.ui.main_window import MainWindow

# Setup logging
logger = setup_logging()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("4Charm")
    app.setApplicationVersion("5.2.0")

    # Set application icon
    icon_path = Path(__file__).parent.parent / "assets" / "4Charm.icns"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
