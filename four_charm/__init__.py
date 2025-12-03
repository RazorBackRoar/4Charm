from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("4Charm")
except PackageNotFoundError:
    __version__ = "unknown"
