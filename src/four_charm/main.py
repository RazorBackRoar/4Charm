#!/usr/bin/env python3
"""4Charm - Advanced 4chan Media Downloader
A high-performance GUI application for bulk downloading media from 4chan threads and boards.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from four_charm.gui.main_window import MainWindow
from four_charm.utils.logging_setup import setup_logging


# Setup logging
logger = setup_logging()


def get_version() -> str:
    """Get version from Info.plist (frozen) or pyproject.toml (dev)."""
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
                        version = data.get("CFBundleShortVersionString") or data.get("CFBundleVersion")
                        if version:
                            return str(version)
                    break
        except Exception as e:
            logger.warning("Could not read version from Info.plist: %s", e)
        # Frozen apps should have version in plist; if not, return hardcoded
        return "6.4.2"

    # 2. Development: read from pyproject.toml
    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore

        pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except (OSError, KeyError, ValueError) as e:
        logger.warning("Could not read version from pyproject.toml: %s", e)
        return "0.0.0"


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("4Charm")
    app.setApplicationVersion(get_version())

    # Set application icon (assets/icons/ is at project root)
    icon_path: Path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        icon_path = Path(sys._MEIPASS) / "assets" / "icons" / "4Charm.icns"  # type: ignore[attr-defined]
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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
