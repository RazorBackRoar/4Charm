from pathlib import Path
from setuptools import setup

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


APP_NAME = "4Charm"
APP_SCRIPT = "src/four_charm/main.py"
APP_VERSION = get_project_version()
BUNDLE_ID = "com.RazorBackRoar.4Charm"
AUTHOR_NAME = "RazorBackRoar"

APP = [APP_SCRIPT]

DATA_FILES = [
    ("assets/icons", ["assets/icons/4Charm.icns"]),
]

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/icons/4Charm.icns",
    "arch": "arm64",
    "plist": {
        "CFBundleIconFile": APP_NAME,
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": APP_VERSION,
        "CFBundleShortVersionString": APP_VERSION,
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
        "LSMinimumSystemVersion": "11.0",
        "LSApplicationCategoryType": "public.app-category.utilities",
        "CFBundleSupportedPlatforms": ["MacOSX"],
        "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
    },
    "packages": ["PySide6", "requests", "urllib3", "certifi", "bs4"],
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
