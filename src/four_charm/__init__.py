"""4Charm - Advanced 4chan Media Downloader."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("4Charm")
except PackageNotFoundError:
    __version__ = "6.4.4"  # Fallback for bundled apps
