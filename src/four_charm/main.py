#!/usr/bin/env python3
"""4Charm - Advanced 4chan Media Downloader.

A high-performance GUI application for bulk downloading media from 4chan threads and boards.
"""

import gc
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from four_charm.gui.main_window import MainWindow
from four_charm.utils.logging_setup import setup_logging
from razorcore.appinfo import print_startup_info
from razorcore.config import get_version as razorcore_get_version


# Setup logging
logger = setup_logging()

APP_NAME = "4Charm"
PACKAGE_NAME = "four-charm"


def get_version() -> str:
    """Get version from Info.plist (frozen) or razorcore/pyproject (dev)."""
    # 1. Frozen app: read from Info.plist
    if getattr(sys, "frozen", False):
        try:
            import plistlib

            exe_path = Path(sys.executable)
            for parent in exe_path.parents:
                if parent.suffix == ".app":
                    info_plist = parent / "Contents" / "Info.plist"
                    if info_plist.exists():
                        with info_plist.open("rb") as f:
                            data = plistlib.load(f)
                        version = data.get("CFBundleShortVersionString") or data.get(
                            "CFBundleVersion"
                        )
                        if version:
                            return str(version)
                    break
        except Exception as e:
            logger.warning("Could not read version from Info.plist: %s", e)
        # Frozen apps should have version in plist; if not, return hardcoded
        return "1.0.0"

    # 2. Development: razorcore version resolution
    pyproject_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    return razorcore_get_version(
        default="0.0.0",
        package_name=PACKAGE_NAME,
        pyproject_path=pyproject_path if pyproject_path.exists() else None,
    )


def main() -> None:
    """Main application entry point."""
    print_startup_info(APP_NAME, package_name=PACKAGE_NAME)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(get_version())

    # Set application icon (assets/icons/ is at project root)
    icon_path: Path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        icon_path = Path(sys._MEIPASS) / "assets" / "icons" / "4Charm.icns"
    else:
        icon_path = (
            Path(__file__).parent.parent.parent.parent
            / "assets"
            / "icons"
            / "4Charm.icns"
        )
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    # Ensure complete cleanup on exit
    exit_code = app.exec()

    # Force cleanup of all resources
    app.deleteLater()
    gc.collect()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
