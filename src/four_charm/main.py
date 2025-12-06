#!/usr/bin/env python3
"""
4Charm - Advanced 4chan Media Downloader
A high-performance GUI application for bulk downloading media from 4chan threads and boards.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from four_charm.utils.logging_setup import setup_logging
from four_charm.gui.main_window import MainWindow

# Setup logging
logger = setup_logging()


def get_version() -> str:
    """Get version from pyproject.toml."""
    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore

        # pyproject.toml is at project root (3 levels up from this file)
        pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except Exception as e:
        logger.warning(f"Could not read version from pyproject.toml: {e}")
        return "5.2.0"


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("4Charm")
    app.setApplicationVersion(get_version())

    # Set application icon (assets/icons/ is at project root)
    icon_path = Path(__file__).parent.parent.parent.parent / "assets" / "icons" / "4Charm.icns"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
