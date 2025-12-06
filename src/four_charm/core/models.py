import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging
from ..config import Config

logger = logging.getLogger("4Charm")


class DownloadQueue:
    """Manage download queue without UI changes"""

    def __init__(self):
        self.queue = []
        self.history = []
        self.active_downloads = []
        self.completed = []
        self.failed = []

    def add_url(self, url: str) -> None:
        """Add URL to download queue"""
        if url not in self.queue and url not in self.active_downloads:
            self.queue.append(url)
            logger.info(f"Added URL to queue: {url}")

    def remove_url(self, index: int) -> None:
        """Remove URL from queue by index"""
        if 0 <= index < len(self.queue):
            removed_url = self.queue.pop(index)
            logger.info(f"Removed URL from queue: {removed_url}")

    def start_download(self, url: str) -> None:
        """Move URL from queue to active downloads"""
        if url in self.queue:
            self.queue.remove(url)
        if url not in self.active_downloads:
            self.active_downloads.append(url)

    def complete_download(self, url: str) -> None:
        """Mark URL as completed"""
        if url in self.active_downloads:
            self.active_downloads.remove(url)
        if url not in self.completed:
            self.completed.append(url)
            self.history.append(
                {"url": url, "completed_at": datetime.now(), "status": "completed"}
            )

    def fail_download(self, url: str, error: Optional[Exception] = None) -> None:
        """Mark URL as failed"""
        if url in self.active_downloads:
            self.active_downloads.remove(url)
        if url not in self.failed:
            self.failed.append(url)
            self.history.append(
                {
                    "url": url,
                    "completed_at": datetime.now(),
                    "status": "failed",
                    "error": str(error),
                }
            )

    def get_stats(self) -> dict[str, int]:
        """Get queue statistics"""
        return {
            "queued": len(self.queue),
            "active": len(self.active_downloads),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "total": len(self.queue)
            + len(self.active_downloads)
            + len(self.completed)
            + len(self.failed),
        }

    def clear_completed(self) -> None:
        """Clear completed and failed lists"""
        self.completed.clear()
        self.failed.clear()

    def clear_all(self) -> None:
        """Clear all queues"""
        self.queue.clear()
        self.active_downloads.clear()
        self.completed.clear()
        self.failed.clear()
        self.history.clear()


class MediaFile:
    """Represents a downloadable media file."""

    def __init__(self, url: str, filename: str, board: str = "", thread_id: str = ""):
        self.url = url
        self.filename = filename
        self.board = board
        self.thread_id = thread_id
        self.size = 0
        self.downloaded = False
        self.download_speed = 0.0
        self.start_time: Optional[float] = None
        self.hash: Optional[str] = None

    def calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file for duplicate detection."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(Config.CHUNK_SIZE), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
