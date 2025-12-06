import sys
from pathlib import Path

sys.path.insert(0, "src")

from setuptools import setup, find_packages

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


def get_project_version(default: str = "0.0.0") -> str:
    pyproject = Path(__file__).resolve().parent / "pyproject.toml"
    if not pyproject.exists():
        return default
    try:
        with pyproject.open("rb") as fp:
            data = tomllib.load(fp)
        return data["project"]["version"]
    except Exception:
        return default


# --- Application Configuration (Single Source of Truth) ---
APP_NAME = "4Charm"
APP_SCRIPT = "src/four_charm/main.py"
APP_VERSION = get_project_version()
BUNDLE_ID = "com.RazorBackRoar.4Charm"
AUTHOR_NAME = "RazorBackRoar"

# --- Resource Files ---
DATA_FILES = [
    ("assets/icons", ["assets/icons/4Charm.icns"]),
]

# --- Info.plist Configuration ---
PLIST = {
    "CFBundleIconFile": APP_NAME,
    "CFBundleName": APP_NAME,
    "CFBundleDisplayName": APP_NAME,
    "CFBundleIdentifier": BUNDLE_ID,
    "CFBundleVersion": APP_VERSION,
    "CFBundleShortVersionString": APP_VERSION,
    "NSHumanReadableCopyright": f"Copyright © 2025 {AUTHOR_NAME}. All rights reserved.",
    "NSHighResolutionCapable": True,
    "NSRequiresAquaSystemAppearance": False,
    "LSMinimumSystemVersion": "11.0",
    "LSRequiresNativeExecution": True,
    "LSApplicationCategoryType": "public.app-category.utilities",
    "CFBundleSupportedPlatforms": ["MacOSX"],
    "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
}

# --- py2app Options ---
OPTIONS = {
    "iconfile": "assets/icons/4Charm.icns",
    "packages": ["four_charm", "PySide6", "requests", "urllib3", "certifi", "bs4"],
    "plist": PLIST,
    "bdist_base": "build/temp",
    "dist_dir": "build/dist",
    "strip": True,
    "argv_emulation": False,
    "arch": "arm64",
    "includes": [
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtGui",
    ],
    "excludes": [
        "PyQt6",
        "PyQt5",
        "sip",
        "tkinter",
        "test",
        "unittest",
        "PyInstaller",
        "numpy",
        "pandas",
        "IPython",
        "jupyter_client",
        "ipykernel",
        "tornado",
        "zmq",
        "PIL",
        "botocore",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtNetwork",
        "PySide6.QtMultimedia",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtDesigner",
        "PySide6.QtXml",
        "PySide6.QtSvg",
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtBluetooth",
        "PySide6.QtDBus",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtPrintSupport",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSensors",
        "PySide6.QtSerialBus",
        "PySide6.QtSerialPort",
        "PySide6.QtStateMachine",
        "PySide6.QtTextToSpeech",
        "PySide6.QtWebChannel",
        "PySide6.QtWebSockets",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DAnimation",
    ],
    "optimize": 2,
    "compressed": True,
    "no_chdir": True,
}

# --- Setup Definition ---
setup(
    app=[APP_SCRIPT],
    name=APP_NAME,
    author=AUTHOR_NAME,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
