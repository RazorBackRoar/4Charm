from setuptools import setup
import py2app

APP = ["main.py"]

DATA_FILES = [
    ("resources", ["resources/4Charm.icns"]),
]

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "resources/4Charm.icns",
    "arch": "arm64",
    "plist": {
        "CFBundleIconFile": "4Charm",
        "CFBundleName": "4Charm",
        "CFBundleDisplayName": "4Charm",
        "CFBundleIdentifier": "com.RazorBackRoar.4Charm",
        "CFBundleVersion": "3.0.0",
        "CFBundleShortVersionString": "3.0.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "LSMinimumSystemVersion": "11.0",
        "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
    },
    "packages": ["PySide6", "requests", "urllib3", "certifi", "bs4"],
    # Explicitly excluding PyQt6 is good practice
    "excludes": ["PyQt6", "PyQt5", "tkinter", "test", "unittest"],
    "includes": ["PySide6.QtCore", "PySide6.QtWidgets", "PySide6.QtGui"],
    "optimize": 2,
    "compressed": True,
    "no_chdir": True,
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
)
