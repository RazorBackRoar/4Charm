#!/usr/bin/env python3
"""
4Charm - Advanced 4chan Media Downloader
A high-performance GUI application for bulk downloading media from 4chan threads and boards.
Version: 3.0.0
"""

import os
import re
import sys
import time
import logging
import multiprocessing
import shutil
import hashlib
import json
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QFrame,
    QTextEdit,
    QProgressBar,
    QMessageBox,
    QStatusBar,
    QSizePolicy,
    QFileDialog,
)
from PySide6.QtCore import Qt, Signal, QObject, QThread, QTimer, QUrl, QMutex
from PySide6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QDesktopServices,
    QTextCursor,
    QKeySequence,
    QShortcut,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Configuration constants
class Config:
    MAX_WORKERS = min(5, multiprocessing.cpu_count())
    DOWNLOAD_TIMEOUT = (10, 60)
    RATE_LIMIT_DELAY = 0.3
    MAX_RETRIES = 3
    CHUNK_SIZE = 8192
    MAX_FILENAME_LENGTH = 200
    MIN_FREE_SPACE_MB = 100
    PROGRESS_UPDATE_INTERVAL = 0.1
    MAX_FOLDER_NAME_LENGTH = 60

    # Smart rate limiting
    BASE_DELAY = 0.3
    BACKOFF_MULTIPLIER = 1.5
    MAX_DELAY = 5.0

    MEDIA_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".webm",
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".pdf",
        ".txt",
        ".zip",
        ".rar",
    }

    PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    VIDEO_EXTENSIONS = {".webm", ".mp4", ".mov", ".avi", ".mkv"}

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class DownloadQueue:
    """Manage download queue without UI changes"""

    def __init__(self):
        self.queue = []
        self.history = []
        self.active_downloads = []
        self.completed = []
        self.failed = []

    def add_url(self, url):
        """Add URL to download queue"""
        if url not in self.queue and url not in self.active_downloads:
            self.queue.append(url)
            logger.info(f"Added URL to queue: {url}")

    def remove_url(self, index):
        """Remove URL from queue by index"""
        if 0 <= index < len(self.queue):
            removed_url = self.queue.pop(index)
            logger.info(f"Removed URL from queue: {removed_url}")

    def start_download(self, url):
        """Move URL from queue to active downloads"""
        if url in self.queue:
            self.queue.remove(url)
        if url not in self.active_downloads:
            self.active_downloads.append(url)

    def complete_download(self, url):
        """Mark URL as completed"""
        if url in self.active_downloads:
            self.active_downloads.remove(url)
        if url not in self.completed:
            self.completed.append(url)
            self.history.append(
                {"url": url, "completed_at": datetime.now(), "status": "completed"}
            )

    def fail_download(self, url, error=None):
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

    def get_stats(self):
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

    def clear_completed(self):
        """Clear completed and failed lists"""
        self.completed.clear()
        self.failed.clear()

    def clear_all(self):
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


class FourChanScraper:
    """Enhanced scraper for 4chan media files with concurrent downloads."""

    def __init__(self):
        # Don't set a default folder - let user choose on first download
        self.download_dir: Optional[Path] = None
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=Config.MAX_WORKERS * 2,
            pool_maxsize=Config.MAX_WORKERS * 2,
            max_retries=Config.MAX_RETRIES,
            pool_block=False,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": Config.USER_AGENT,
                "Accept": "application/json, text/html, */*",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "DNT": "1",
                "Pragma": "no-cache",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        self.stats = {
            "total": 0,
            "downloaded": 0,
            "failed": 0,
            "skipped": 0,
            "size_mb": 0.0,
            "download_speed": 0.0,
            "start_time": None,
            "duplicates": 0,
            "current_speed": 0.0,
        }
        self.downloaded_hashes = set()
        self.paused = False
        self.cancelled = False
        self.stats_mutex = QMutex()
        self.current_delay = Config.BASE_DELAY
        self.download_queue = DownloadQueue()

    def adaptive_delay(self, success=True):
        """Adaptive rate limiting based on success/failure"""
        if success:
            self.current_delay = max(Config.BASE_DELAY, self.current_delay / 1.1)
        else:
            self.current_delay = min(
                Config.MAX_DELAY, self.current_delay * Config.BACKOFF_MULTIPLIER
            )
        time.sleep(self.current_delay)

    def handle_network_error(self, error, url, context=""):
        """Handle different types of network errors with appropriate responses"""
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "url": url,
            "context": context,
        }

        if isinstance(error, requests.exceptions.ConnectionError):
            logger.error(f"Connection error {context} for {url}: {str(error)}")
            self.adaptive_delay(success=False)
            error_info["category"] = "connection"
            return error_info

        elif isinstance(error, requests.exceptions.Timeout):
            logger.error(f"Timeout error {context} for {url}: {str(error)}")
            self.adaptive_delay(success=False)
            error_info["category"] = "timeout"
            return error_info

        elif isinstance(error, requests.exceptions.HTTPError):
            status_code = getattr(error.response, "status_code", 0)
            error_info["status_code"] = status_code

            if status_code == 429:  # Rate limited
                logger.warning(f"Rate limited by server for {url}, increasing delay")
                self.current_delay = min(Config.MAX_DELAY, self.current_delay * 2)
                time.sleep(self.current_delay)
                error_info["category"] = "rate_limited"
                return error_info

            elif status_code in [403, 404]:
                logger.error(f"Access denied or not found for {url}: {status_code}")
                self.adaptive_delay(success=False)
                error_info["category"] = "access"
                return error_info

            else:
                logger.error(
                    f"HTTP error {status_code} {context} for {url}: {str(error)}"
                )
                self.adaptive_delay(success=False)
                error_info["category"] = "http"
                return error_info

        elif isinstance(error, requests.exceptions.TooManyRedirects):
            logger.error(f"Too many redirects {context} for {url}: {str(error)}")
            self.adaptive_delay(success=False)
            error_info["category"] = "redirects"
            return error_info

        else:
            logger.error(f"Unknown error {context} for {url}: {str(error)}")
            self.adaptive_delay(success=False)
            error_info["category"] = "unknown"
            return error_info

    def sanitize_filename(self, filename: str) -> str:
        """Enhanced filename sanitization with security improvements."""
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        name_part = sanitized.split(".")[0].upper()
        if name_part in reserved_names:
            sanitized = f"_{sanitized}"

        if len(sanitized) > Config.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(sanitized)
            max_name_len = Config.MAX_FILENAME_LENGTH - len(ext)
            sanitized = name[:max_name_len] + ext

        return sanitized or "unnamed_file"

    def _sanitize_folder_component(self, name: str) -> str:
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or "")
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return sanitized

    def build_session_base_name(self, parsed_url: Dict) -> str:
        board = parsed_url.get("board", "").strip()
        url_type = parsed_url.get("type")
        thread_id = parsed_url.get("thread_id")
        if url_type == "thread" and thread_id:
            base_name = f"{board}-{thread_id}"
        elif url_type == "catalog":
            base_name = f"{board}-catalog"
        else:
            base_name = board or "4chan"
        base_name = self._sanitize_folder_component(base_name)
        if len(base_name) > Config.MAX_FOLDER_NAME_LENGTH:
            base_name = base_name[: Config.MAX_FOLDER_NAME_LENGTH]
        base_name = base_name.rstrip("-_ ")
        return base_name or "session"

    def build_thread_folder_name(
        self, thread_title: Optional[str], thread_id: str, board: str
    ) -> str:
        """Build folder name for thread using title only."""
        if thread_title:
            # Sanitize the thread title for folder name
            folder_name = self._sanitize_folder_component(thread_title)
            # Truncate if too long
            if len(folder_name) > Config.MAX_FOLDER_NAME_LENGTH:
                folder_name = folder_name[: Config.MAX_FOLDER_NAME_LENGTH].rstrip("-_ ")
        else:
            # If no title, use thread ID as the folder name
            folder_name = thread_id

        return folder_name or thread_id

    def check_disk_space(self, required_mb: float = 0) -> bool:
        """Check if sufficient disk space is available."""
        if self.download_dir is None:
            return False
        try:
            free_space_bytes = shutil.disk_usage(self.download_dir).free
            free_space_mb = free_space_bytes / (1024 * 1024)
            return free_space_mb > (Config.MIN_FREE_SPACE_MB + required_mb)
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            return True

    def parse_url(self, url: str) -> Optional[Dict]:
        """Parse 4chan URL to extract board and thread info."""
        try:
            url = url.strip()
            if not url.startswith("http"):
                url = "https://" + url
            if "boards.4chan.org" not in url and "4chan.org" not in url:
                return None
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split("/") if p]
            if not path_parts:
                return None
            board = path_parts[0]
            result = {"board": board, "type": "board", "thread_id": None}
            if len(path_parts) >= 3 and path_parts[1] == "thread":
                thread_id = path_parts[2].split("#")[0]
                if thread_id.isdigit():
                    result["type"] = "thread"
                    result["thread_id"] = thread_id
            elif len(path_parts) >= 2 and path_parts[1] == "catalog":
                result["type"] = "catalog"
            return result
        except Exception as e:
            logger.error(f"URL parsing error: {e}")
            return None

    def get_thread_data(self, board: str, thread_id: str) -> Optional[Dict]:
        """Fetch thread JSON data from 4chan API with adaptive rate limiting."""
        self.adaptive_delay()  # Adaptive rate limiting
        api_url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
        try:
            response = self.session.get(api_url, timeout=30)
            response.raise_for_status()
            thread_data = response.json()
            # Extract thread title from the first post (OP)
            posts = thread_data.get("posts", [])
            thread_title = None
            if posts and "sub" in posts[0]:
                thread_title = posts[0]["sub"]
            thread_data["_thread_title"] = thread_title
            self.adaptive_delay(success=True)  # Success, reduce delay
            return thread_data
        except Exception as e:
            error_info = self.handle_network_error(e, api_url, "getting thread data")
            if error_info.get("category") == "rate_limited":
                # Retry once after rate limit handling
                try:
                    time.sleep(2)
                    response = self.session.get(api_url, timeout=30)
                    response.raise_for_status()
                    thread_data = response.json()
                    posts = thread_data.get("posts", [])
                    thread_title = None
                    if posts and "sub" in posts[0]:
                        thread_title = posts[0]["sub"]
                    thread_data["_thread_title"] = thread_title
                    return thread_data
                except Exception as e2:
                    logger.error(f"Retry failed for {api_url}: {e2}")
                    return None
            return None

    def get_catalog_data(self, board: str) -> Optional[List]:
        """Fetch catalog data from 4chan API with adaptive rate limiting."""
        self.adaptive_delay()  # Adaptive rate limiting
        api_url = f"https://a.4cdn.org/{board}/catalog.json"
        try:
            response = self.session.get(api_url, timeout=30)
            response.raise_for_status()
            catalog_data = response.json()
            self.adaptive_delay(success=True)  # Success, reduce delay
            return catalog_data
        except Exception as e:
            error_info = self.handle_network_error(e, api_url, "getting catalog data")
            if error_info.get("category") == "rate_limited":
                # Retry once after rate limit handling
                try:
                    time.sleep(2)
                    response = self.session.get(api_url, timeout=30)
                    response.raise_for_status()
                    return response.json()
                except Exception as e2:
                    logger.error(f"Retry failed for {api_url}: {e2}")
                    return None
            return None

    def extract_media_from_posts(
        self, posts: List[Dict], board: str, thread_id: str = ""
    ) -> List[MediaFile]:
        """Extract media files from posts."""
        media_files = []
        for post in posts:
            if "tim" in post and "ext" in post:
                ext = post["ext"].lower()
                if ext in Config.MEDIA_EXTENSIONS:
                    filename = f"{post['tim']}{ext}"
                    original_name = post.get("filename", "unnamed") + ext
                    media_url = f"https://i.4cdn.org/{board}/{filename}"
                    safe_filename = self.sanitize_filename(original_name)
                    media_file = MediaFile(
                        url=media_url,
                        filename=safe_filename,
                        board=board,
                        thread_id=thread_id,
                    )
                    media_files.append(media_file)
        return media_files

    def scrape_thread(
        self, board: str, thread_id: str
    ) -> Tuple[List[MediaFile], Optional[str]]:
        """Get all media files from a specific thread."""
        logger.info(f"Scraping thread /{board}/{thread_id}")
        thread_data = self.get_thread_data(board, thread_id)
        if not thread_data:
            return [], None
        posts = thread_data.get("posts", [])
        thread_title = thread_data.get("_thread_title")
        media_files = self.extract_media_from_posts(posts, board, thread_id)
        return media_files, thread_title

    def scrape_catalog(self, board: str, max_threads: int = 10) -> List[MediaFile]:
        """Get media files from recent threads in catalog."""
        logger.info(f"Scraping catalog /{board}/ (max {max_threads} threads)")
        catalog_data = self.get_catalog_data(board)
        if not catalog_data:
            return []
        media_files = []
        threads_processed = 0
        for page in catalog_data:
            if threads_processed >= max_threads:
                break
            for thread in page.get("threads", []):
                if threads_processed >= max_threads:
                    break
                thread_id = str(thread.get("no", ""))
                if thread_id.isdigit():
                    thread_media, _thread_title = self.scrape_thread(board, thread_id)
                    media_files.extend(thread_media)
                    threads_processed += 1
                    time.sleep(0.5)
        return media_files

    def download_file(
        self,
        media_file: MediaFile,
        url_folder_name: Optional[str] = None,
        progress_callback=None,
    ) -> bool:
        """Enhanced download with progress tracking, duplicate detection, and resume capability."""
        # Ensure download directory is set
        if self.download_dir is None:
            logger.error("Download directory not set")
            return False

        # Track download in queue
        self.download_queue.start_download(media_file.url)

        if self.cancelled:
            self.download_queue.fail_download(media_file.url, "Cancelled")
            return False

        while self.paused:
            time.sleep(0.1)
            if self.cancelled:
                self.download_queue.fail_download(media_file.url, "Cancelled")
                return False

        for attempt in range(Config.MAX_RETRIES):
            try:
                # Create thread-specific folder
                if url_folder_name:
                    thread_dir = self.download_dir / url_folder_name
                else:
                    thread_dir = self.download_dir / "misc"
                thread_dir.mkdir(parents=True, exist_ok=True)

                # Determine save directory based on file extension
                if media_file.filename.lower().endswith(".webm"):
                    # Create WEBM subfolder for .webm files
                    save_dir = thread_dir / "WEBM"
                    save_dir.mkdir(parents=True, exist_ok=True)
                else:
                    # All other files go to main thread folder
                    save_dir = thread_dir

                file_path = save_dir / media_file.filename

                # Check for existing complete file
                if file_path.exists() and file_path.stat().st_size > 0:
                    try:
                        file_hash = media_file.calculate_hash(file_path)
                        if file_hash in self.downloaded_hashes:
                            self.stats_mutex.lock()
                            self.stats["duplicates"] += 1
                            self.stats_mutex.unlock()
                            self.download_queue.complete_download(media_file.url)
                            return True
                        self.downloaded_hashes.add(file_hash)
                    except Exception:
                        pass

                    self.stats_mutex.lock()
                    self.stats["skipped"] += 1
                    self.stats_mutex.unlock()
                    media_file.downloaded = True
                    self.download_queue.complete_download(media_file.url)
                    return True

                if not self.check_disk_space():
                    logger.error("Insufficient disk space")
                    self.stats_mutex.lock()
                    self.stats["failed"] += 1
                    self.stats_mutex.unlock()
                    self.download_queue.fail_download(
                        media_file.url, "Insufficient disk space"
                    )
                    return False

                # Check for partial download and attempt resume
                headers = {}
                existing_size = 0
                if file_path.exists():
                    existing_size = file_path.stat().st_size
                    if existing_size > 0:
                        headers["Range"] = f"bytes={existing_size}-"
                        logger.info(
                            f"Resuming {media_file.filename} from byte {existing_size}"
                        )

                media_file.start_time = time.time()
                response = self.session.get(
                    media_file.url,
                    headers=headers,  # Add resume headers
                    stream=True,
                    timeout=Config.DOWNLOAD_TIMEOUT,
                    allow_redirects=True,
                )

                # Handle resume response
                if response.status_code == 206:  # Partial content
                    mode = "ab"  # Append to existing file
                    logger.info(f"Resuming download of {media_file.filename}")
                elif response.status_code == 200:  # Full content
                    mode = "wb"  # Overwrite file
                    existing_size = 0
                    if file_path.exists():
                        file_path.unlink()  # Remove partial file
                else:
                    response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                if existing_size > 0 and total_size > 0:
                    total_size += existing_size

                downloaded_size = existing_size

                with open(file_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=Config.CHUNK_SIZE):
                        if self.cancelled:
                            return False

                        while self.paused:
                            time.sleep(0.1)
                            if self.cancelled:
                                return False

                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)

                            elapsed = time.time() - media_file.start_time
                            if elapsed > 0:
                                media_file.download_speed = (
                                    downloaded_size / elapsed / 1024 / 1024
                                )

                            if progress_callback and total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                progress_callback(progress, media_file.download_speed)

                file_size = file_path.stat().st_size
                if file_size == 0:
                    file_path.unlink(missing_ok=True)
                    raise Exception("Downloaded file is empty")

                try:
                    media_file.hash = media_file.calculate_hash(file_path)
                    self.downloaded_hashes.add(media_file.hash)
                except Exception as e:
                    logger.warning(
                        f"Could not calculate hash for {media_file.filename}: {e}"
                    )

                media_file.size = file_size
                media_file.downloaded = True
                self.stats_mutex.lock()
                self.stats["downloaded"] += 1
                self.stats["size_mb"] += file_size / (1024 * 1024)
                self.stats["current_speed"] = media_file.download_speed
                self.stats_mutex.unlock()

                # Mark as completed in queue
                self.download_queue.complete_download(media_file.url)
                return True

            except Exception as e:
                logger.warning(
                    f"Download attempt {attempt + 1}/{Config.MAX_RETRIES} failed for {media_file.filename}: {e}"
                )
                if attempt == Config.MAX_RETRIES - 1:
                    logger.error(
                        f"Download failed permanently for {media_file.filename}: {e}"
                    )
                    self.stats_mutex.lock()
                    self.stats["failed"] += 1
                    self.stats_mutex.unlock()
                    # Mark as failed in queue
                    self.download_queue.fail_download(media_file.url, str(e))
                    return False
                time.sleep(2**attempt)

        # If we exit the loop without success, mark as failed
        self.download_queue.fail_download(media_file.url, "Max retries exceeded")
        return False

    def pause_downloads(self):
        self.paused = True

    def resume_downloads(self):
        self.paused = False

    def cancel_downloads(self):
        self.cancelled = True
        self.paused = False


class DownloadWorker(QObject):
    """Enhanced worker thread for concurrent downloads."""

    progress = Signal(int, int, str, float, str, int)
    log_message = Signal(str)
    finished = Signal(dict)
    speed_update = Signal(float)

    def __init__(self, scraper: FourChanScraper, parsed_url: Dict):
        super().__init__()
        self.scraper = scraper
        self.parsed_url = parsed_url

    def run(self):
        """Enhanced concurrent download logic."""
        try:
            board = self.parsed_url["board"]
            url_type = self.parsed_url["type"]
            thread_id = self.parsed_url.get("thread_id")

            if url_type == "thread" and thread_id:
                url_folder_name = self.scraper.build_session_base_name(self.parsed_url)
                media_files, _thread_title = self.scraper.scrape_thread(
                    board, thread_id
                )
            elif url_type == "catalog":
                url_folder_name = self.scraper.build_session_base_name(self.parsed_url)
                media_files = self.scraper.scrape_catalog(board, 10)
            else:
                url_folder_name = self.scraper.build_session_base_name(self.parsed_url)
                media_files = self.scraper.scrape_catalog(board, 5)

            if not media_files:
                self.log_message.emit("❌ No media files found!")
                self.finished.emit(self.scraper.stats)
                return

            self.scraper.stats["total"] = len(media_files)
            self.scraper.stats["start_time"] = time.time()
            self.log_message.emit(f"📁 Found {len(media_files)} media files")

            completed = 0
            with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
                future_to_media = {
                    executor.submit(
                        self.scraper.download_file, media, url_folder_name
                    ): media
                    for media in media_files
                }

                for future in as_completed(future_to_media):
                    if self.scraper.cancelled:
                        self.log_message.emit("🛑 Download cancelled")
                        break

                    media_file = future_to_media[future]
                    completed += 1

                    try:
                        success = future.result()
                        if success:
                            speed_info = (
                                f" ({media_file.download_speed:.1f} MB/s)"
                                if media_file.download_speed > 0
                                else ""
                            )
                            self.log_message.emit(
                                f"✅ {media_file.filename}{speed_info}"
                            )
                        else:
                            self.log_message.emit(f"❌ Failed: {media_file.filename}")
                    except Exception as e:
                        self.log_message.emit(
                            f"❌ Error downloading {media_file.filename}: {e}"
                        )

                    avg_speed = self._calculate_average_speed()
                    self.progress.emit(
                        completed,
                        len(media_files),
                        media_file.filename,
                        avg_speed,
                        "",
                        0,
                    )
                    self.speed_update.emit(avg_speed)

            stats = self.scraper.stats
            total_time = time.time() - (stats["start_time"] or time.time())
            avg_speed = stats["size_mb"] / total_time if total_time > 0 else 0

            self.log_message.emit(
                f"🎉 Complete! {stats['downloaded']}/{stats['total']} files "
                f"({stats['size_mb']:.1f}MB) in {total_time:.1f}s - Avg: {avg_speed:.1f} MB/s"
            )
            if stats["duplicates"] > 0:
                self.log_message.emit(
                    f"🔄 Skipped {stats['duplicates']} duplicate files"
                )

            self.finished.emit(stats)
        except Exception as e:
            self.log_message.emit(f"💥 Error: {e}")
            self.finished.emit(self.scraper.stats)

    def _calculate_average_speed(self) -> float:
        """Calculate current average download speed."""
        self.scraper.stats_mutex.lock()
        try:
            if self.scraper.stats["start_time"]:
                elapsed = time.time() - self.scraper.stats["start_time"]
                if elapsed > 0:
                    return self.scraper.stats["size_mb"] / elapsed
            return 0.0
        finally:
            self.scraper.stats_mutex.unlock()

    def cancel(self):
        self.scraper.cancel_downloads()

    def pause(self):
        self.scraper.pause_downloads()

    def resume(self):
        self.scraper.resume_downloads()


class MultiUrlDownloadWorker(QObject):
    """Worker for concurrent downloads from multiple URLs."""

    progress = Signal(
        int, int, str, float, str, int
    )  # added thread_name and thread_index
    log_message = Signal(str)
    finished = Signal(dict)
    speed_update = Signal(float)

    def __init__(self, scraper: FourChanScraper, parsed_urls: List[Dict]):
        super().__init__()
        self.scraper = scraper
        self.parsed_urls = parsed_urls
        self.thread_pool = None

    def run(self):
        """Run concurrent downloads from multiple URLs."""
        try:
            total_files = 0
            url_tasks = []

            # First pass: scrape all URLs to get media counts
            for i, parsed_url in enumerate(self.parsed_urls):
                board = parsed_url["board"]
                url_type = parsed_url["type"]
                thread_id = parsed_url.get("thread_id")

                if url_type == "thread" and thread_id:
                    media_files, thread_title = self.scraper.scrape_thread(
                        board, thread_id
                    )
                    folder_name = self.scraper.build_thread_folder_name(
                        thread_title, thread_id, board
                    )
                    url_tasks.append(
                        {
                            "parsed_url": parsed_url,
                            "media_files": media_files,
                            "folder_name": folder_name,
                            "thread_title": thread_title or f"Thread {thread_id}",
                            "url_index": i,
                        }
                    )
                    total_files += len(media_files)
                    self.log_message.emit(
                        f"📁 [{i+1}/{len(self.parsed_urls)}] Found {len(media_files)} files in '{folder_name}'"
                    )
                elif url_type == "catalog":
                    media_files = self.scraper.scrape_catalog(board, 10)
                    folder_name = self.scraper.build_session_base_name(parsed_url)
                    url_tasks.append(
                        {
                            "parsed_url": parsed_url,
                            "media_files": media_files,
                            "folder_name": folder_name,
                            "thread_title": f"{board} catalog",
                            "url_index": i,
                        }
                    )
                    total_files += len(media_files)
                    self.log_message.emit(
                        f"📁 [{i+1}/{len(self.parsed_urls)}] Found {len(media_files)} files in '{folder_name}'"
                    )
                else:
                    media_files = self.scraper.scrape_catalog(board, 5)
                    folder_name = self.scraper.build_session_base_name(parsed_url)
                    url_tasks.append(
                        {
                            "parsed_url": parsed_url,
                            "media_files": media_files,
                            "folder_name": folder_name,
                            "thread_title": f"{board} board",
                            "url_index": i,
                        }
                    )
                    total_files += len(media_files)
                    self.log_message.emit(
                        f"📁 [{i+1}/{len(self.parsed_urls)}] Found {len(media_files)} files in '{folder_name}'"
                    )

            if total_files == 0:
                self.log_message.emit("❌ No media files found in any URLs!")
                self.finished.emit(self.scraper.stats)
                return

            self.scraper.stats["total"] = total_files
            self.scraper.stats["start_time"] = time.time()
            self.log_message.emit(
                f"🚀 Starting concurrent download of {total_files} files from {len(url_tasks)} URLs"
            )

            # Second pass: download all files concurrently
            completed = 0
            with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
                future_to_file = {}

                # Submit all downloads
                for task in url_tasks:
                    folder_name = task["folder_name"]
                    for media_file in task["media_files"]:
                        future = executor.submit(
                            self.scraper.download_file, media_file, folder_name
                        )
                        future_to_file[future] = (media_file, task)

                # Process completions
                for future in as_completed(future_to_file):
                    if self.scraper.cancelled:
                        self.log_message.emit("🛑 Download cancelled")
                        break

                    media_file, task = future_to_file[future]
                    completed += 1

                    try:
                        success = future.result()
                        if success:
                            speed_info = (
                                f" ({media_file.download_speed:.1f} MB/s)"
                                if media_file.download_speed > 0
                                else ""
                            )
                            self.log_message.emit(
                                f"✅ [{task['url_index']+1}] {media_file.filename}{speed_info}"
                            )
                        else:
                            self.log_message.emit(
                                f"❌ [{task['url_index']+1}] Failed: {media_file.filename}"
                            )
                    except Exception as e:
                        self.log_message.emit(
                            f"❌ [{task['url_index']+1}] Error downloading {media_file.filename}: {e}"
                        )

                    avg_speed = self._calculate_average_speed()
                    self.progress.emit(
                        completed,
                        total_files,
                        media_file.filename,
                        avg_speed,
                        task["thread_title"],
                        task["url_index"] + 1,
                    )
                    self.speed_update.emit(avg_speed)

            # Final statistics
            stats = self.scraper.stats
            total_time = time.time() - (stats["start_time"] or time.time())
            avg_speed = stats["size_mb"] / total_time if total_time > 0 else 0

            self.log_message.emit(
                f"🎉 Complete! {stats['downloaded']}/{stats['total']} files "
                f"({stats['size_mb']:.1f}MB) from {len(url_tasks)} URLs in {total_time:.1f}s - Avg: {avg_speed:.1f} MB/s"
            )
            if stats["duplicates"] > 0:
                self.log_message.emit(
                    f"🔄 Skipped {stats['duplicates']} duplicate files"
                )

            self.finished.emit(stats)

        except Exception as e:
            self.log_message.emit(f"💥 Error: {e}")
            self.finished.emit(self.scraper.stats)

    def _calculate_average_speed(self) -> float:
        """Calculate current average download speed."""
        self.scraper.stats_mutex.lock()
        try:
            if self.scraper.stats["start_time"]:
                elapsed = time.time() - self.scraper.stats["start_time"]
                if elapsed > 0:
                    return self.scraper.stats["size_mb"] / elapsed
            return 0.0
        finally:
            self.scraper.stats_mutex.unlock()

    def cancel(self):
        self.scraper.cancel_downloads()

    def pause(self):
        self.scraper.pause_downloads()

    def resume(self):
        self.scraper.resume_downloads()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("4chan Downloader")
        self.setMinimumSize(850, 730)
        self.resize(850, 730)
        self.setAcceptDrops(True)

        self.setStyleSheet(
            """
            QMainWindow { background-color: #1a1a1a; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
            QGroupBox { border: 2px solid #4a9eff; margin-top: 12px; padding-top: 8px; padding-bottom: 8px; background-color: transparent; }
            QGroupBox::title { subcontrol-origin: padding; left: 12px; padding: 0 12px; color: #4a9eff; font-size: 26px; font-weight: 700; }
            QLineEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #404040; border-radius: 10px; padding: 12px 16px; font-size: 16px; selection-background-color: #4a9eff; }
            QLineEdit:focus { border: 2px solid #4a9eff; background-color: #353535; }
            QTextEdit { background-color: #2d2d2d; color: #ffffff; border: 2px solid #4a9eff; border-bottom: none; border-radius: 0px; padding: 8px 12px; font-size: 16px; selection-background-color: #4a9eff; line-height: 1.4; }
            QTextEdit:focus { border: 2px solid #4a9eff; background-color: #353535; border-radius: 0px; }
            QLabel { color: #cccccc; font-size: 15px; }
            QPushButton { font-size: 15px; padding: 8px 16px; border-radius: 8px; border: none; min-height: 36px; font-weight: 600; }
            QPushButton:hover { background-color: #5a5a5a; }
            QPushButton:pressed { background-color: #4a4a4a; }
            QPushButton:disabled { background-color: #404040; color: #888888; }
            QPushButton#startBtn { font-size: 15px; background-color: #4a9eff; color: #ffffff; font-weight: 700; border-radius: 8px; }
            QPushButton#startBtn:disabled { background-color: #404040; color: #888888; }
            QPushButton#cancelBtn { font-size: 15px; background-color: #ff4757; color: white; border-radius: 8px; }
            QPushButton#cancelBtn:hover { background-color: #ff3838; }
            QPushButton#pauseBtn { background-color: #ffa502; color: #1a1a1a; font-weight: 700; border-radius: 8px; }
            QPushButton#pauseBtn:hover { background-color: #ff8c00; }
            QProgressBar { border: none; border-radius: 8px; text-align: center; background-color: #2d2d2d; min-height: 24px; font-size: 13px; font-weight: 600; color: #ffffff; }
            QProgressBar::chunk { background-color: #4a9eff; border-radius: 0px; }
            QFrame#sectionFrame { border: none; background-color: transparent; }
            QStatusBar { background-color: #242424; color: #888888; border-top: 1px solid #404040; padding: 8px; font-size: 13px; }
        """
        )

        self.scraper = FourChanScraper()
        self.download_thread: Optional[QThread] = None
        self.download_worker: Optional["MultiUrlDownloadWorker"] = None
        self.is_paused = False

        self.setup_ui()
        self.setup_connections()
        self._update_ui_for_state("idle")
        # Initialize download stats
        self.update_download_stats()

    def setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        header = QLabel("4chan Downloader")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            "font-size: 34px; font-weight: 700; color: #4a9eff; margin: 15px 0;"
        )
        main_layout.addWidget(header)

        instruction = QLabel(
            "Paste or drop multiple 4chan thread URLs (one per line) to download all media files concurrently\nPress Enter to validate & count URLs | Press Ctrl+Enter to start download"
        )
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction.setStyleSheet(
            "color: #888888; font-size: 15px; margin: 15px 0; line-height: 1.5;"
        )
        main_layout.addWidget(instruction)

        url_group = QGroupBox("URLs to Download")
        url_layout = QVBoxLayout(url_group)
        url_layout.setContentsMargins(10, 10, 10, 10)
        url_layout.setSpacing(8)

        # Frame for the URL input area
        url_frame = QFrame()
        url_frame.setFrameShape(QFrame.Shape.Box)
        url_frame.setFrameShadow(QFrame.Shadow.Raised)
        url_frame.setLineWidth(1)
        url_frame.setStyleSheet(
            """
            QFrame {
                border: 1px solid #404040;
                border-radius: 10px;
                background-color: #2d2d2d;
            }
        """
        )

        url_frame_layout = QVBoxLayout(url_frame)
        url_frame_layout.setContentsMargins(5, 5, 5, 5)
        url_frame_layout.setSpacing(0)

        # URL input area
        self.url_input = QTextEdit()
        self.url_input.setAcceptRichText(False)
        self.url_input.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.url_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.url_input.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.url_input.setPlaceholderText(
            "1. https://boards.4chan.org/g/thread/123456789\n2. https://boards.4chan.org/pol/thread/987654321\n3. https://boards.4chan.org/b/thread/555666777\n4. https://boards.4chan.org/v/thread/888999000\n5. https://boards.4chan.org/gif/thread/111222333"
        )
        line_height = self.url_input.fontMetrics().lineSpacing()
        min_lines = 12
        padding = 24
        min_height = (line_height * min_lines) + padding
        max_height = (line_height * (min_lines + 4)) + padding
        self.url_input.setMinimumHeight(min_height)
        self.url_input.setMaximumHeight(max_height)
        self.url_input.setStyleSheet(
            "background-color: #2d2d2d; color: #ffffff; border: none; padding: 12px 16px; font-size: 16px; selection-background-color: #4a9eff; line-height: 1.4;"
        )
        url_frame_layout.addWidget(self.url_input)

        url_layout.addWidget(url_frame)

        # URL counter label at bottom
        self.url_count_label = QLabel("URLs: 0")
        self.url_count_label.setStyleSheet(
            "color: #cccccc; font-size: 14px; font-weight: 500; padding: 4px 0; background-color: transparent;"
        )
        url_layout.addWidget(self.url_count_label)

        main_layout.addWidget(url_group)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(15)
        control_layout.addStretch()

        # Folder chooser button
        self.folder_btn = QPushButton("📁 Choose Folder")
        self.folder_btn.setMinimumWidth(150)
        self.folder_btn.setStyleSheet(
            "color: #ffffff; background-color: #5a5a5a; font-size: 15px; font-weight: 600; padding: 8px 16px; border-radius: 8px;"
        )
        control_layout.addWidget(self.folder_btn)

        self.start_cancel_btn = QPushButton("🚀 Start Download")
        self.start_cancel_btn.setObjectName("startBtn")
        self.start_cancel_btn.setMinimumWidth(180)
        self.start_cancel_btn.setStyleSheet(
            "background-color: #4a9eff; color: #ffffff; font-size: 15px; font-weight: 700; padding: 8px 16px; border-radius: 8px;"
        )
        control_layout.addWidget(self.start_cancel_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMinimumWidth(100)
        self.clear_btn.setStyleSheet(
            "color: #4a9eff; background-color: transparent; border: 2px solid #4a9eff; font-size: 15px; font-weight: 600; padding: 8px 16px; border-radius: 8px;"
        )
        control_layout.addWidget(self.clear_btn)
        self.pause_resume_btn = QPushButton("⏸️ Pause")
        self.pause_resume_btn.setObjectName("pauseBtn")
        control_layout.addWidget(self.pause_resume_btn)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        progress_group = QGroupBox("Download Progress")
        progress_group.setMinimumHeight(150)
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        progress_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to download...")
        self.progress_label.setStyleSheet(
            "font-size: 14px; font-weight: 500; color: #cccccc; padding: 4px 0; background-color: transparent;"
        )
        self.speed_label = QLabel("Speed: 0.0 MB/s")
        self.speed_label.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #4a9eff; padding: 4px 0; background-color: transparent;"
        )

        progress_layout.addWidget(self.progress_bar)

        progress_info_layout = QHBoxLayout()
        progress_info_layout.addWidget(self.progress_label)
        progress_info_layout.addStretch()
        progress_info_layout.addWidget(self.speed_label)

        progress_layout.addLayout(progress_info_layout)

        main_layout.addWidget(progress_group)

        log_group = QGroupBox("Activity Log")
        log_group.setMinimumHeight(200)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(8)

        # Frame for the log area
        log_frame = QFrame()
        log_frame.setFrameShape(QFrame.Shape.Box)
        log_frame.setFrameShadow(QFrame.Shadow.Raised)
        log_frame.setLineWidth(1)
        log_frame.setStyleSheet(
            """
            QFrame {
                border: 1px solid #404040;
                border-radius: 10px;
                background-color: #242424;
            }
        """
        )

        log_frame_layout = QVBoxLayout(log_frame)
        log_frame_layout.setContentsMargins(5, 5, 5, 5)
        log_frame_layout.setSpacing(0)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setStyleSheet(
            "QTextEdit { background-color: #242424; color: #cccccc; border: none; padding: 8px; font-family: 'Monaco', 'Courier New', monospace; font-size: 13px; line-height: 1.4; }"
        )
        log_frame_layout.addWidget(self.log_text)

        log_layout.addWidget(log_frame)

        # Stats labels at bottom
        stats_layout = QHBoxLayout()
        self.folders_label = QLabel("Folders: 0")
        self.folders_label.setStyleSheet(
            "color: #cccccc; font-size: 14px; font-weight: 500; padding: 4px 0; background-color: transparent;"
        )
        self.files_label = QLabel("Files: 0")
        self.files_label.setStyleSheet(
            "color: #cccccc; font-size: 14px; font-weight: 500; padding: 4px 0; background-color: transparent;"
        )
        self.size_label = QLabel("Size: 0 MB")
        self.size_label.setStyleSheet(
            "color: #4a9eff; font-size: 14px; font-weight: 600; padding: 4px 0; background-color: transparent;"
        )

        stats_layout.addWidget(self.folders_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.files_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.size_label)
        log_layout.addLayout(stats_layout)

        main_layout.addWidget(log_group)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Add version label to bottom right of status bar
        version_label = QLabel("v3.0.0")
        version_label.setStyleSheet("font-size: 11px; color: #666; padding: 0 8px;")
        self.status_bar.addPermanentWidget(version_label)

    def setup_connections(self):
        """Connect signals and slots."""
        self.url_input.textChanged.connect(self.validate_urls)
        self.start_cancel_btn.clicked.connect(self.handle_start_cancel_click)
        self.pause_resume_btn.clicked.connect(self.toggle_pause_resume)
        self.clear_btn.clicked.connect(self.clear_urls)
        self.folder_btn.clicked.connect(self.choose_download_folder)

        self.paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self.paste_shortcut.activated.connect(self.paste_from_clipboard)
        self.start_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self.url_input)
        self.start_shortcut.activated.connect(
            self.validate_urls
        )  # Trigger validation on Enter
        self.download_shortcut = QShortcut(
            QKeySequence("Ctrl+Return"),
            self.url_input,
        )
        self.download_shortcut.activated.connect(
            self.handle_start_cancel_click
        )  # Ctrl+Enter to start download
        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.escape_shortcut.activated.connect(self.cancel_or_close)

    def clear_urls(self):
        """Clear all URLs from the input field."""
        self.url_input.clear()
        self.validate_urls()

    def choose_download_folder(self):
        """Open folder chooser dialog to select download location."""
        current_dir = str(self.scraper.download_dir)
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Download Folder", current_dir, QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.scraper.download_dir = Path(folder)
            self.scraper.download_dir.mkdir(parents=True, exist_ok=True)
            self.add_log_message(f"📁 Download folder changed to: {folder}")
            self.status_bar.showMessage(f"Download folder: {folder}")

    def validate_urls(self):
        """Validate the entered URLs, auto-number them, and update UI accordingly."""
        if getattr(self, "_renumbering", False):
            return  # avoid recursion while renumbering

        raw_text = self.url_input.toPlainText().strip()
        raw_lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]

        # Strip any existing leading numbering (e.g. "1. ")
        cleaned_urls: list[str] = [re.sub(r"^\d+\.\s*", "", ln) for ln in raw_lines]

        # Auto-number
        numbered_lines = [f"{i+1}. {u}" for i, u in enumerate(cleaned_urls)]
        numbered_text = "\n".join(numbered_lines)

        # Replace text only if different to prevent cursor flicker
        if numbered_text != raw_text:
            self._renumbering = True
            self.url_input.setPlainText(numbered_text)
            cursor = self.url_input.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.url_input.setTextCursor(cursor)
            self._renumbering = False
            self._scroll_url_input_to_end()

        urls = cleaned_urls

        # Update the URL counter label
        self.url_count_label.setText(f"URLs: {len(cleaned_urls)}")

        if not urls:
            self.start_cancel_btn.setEnabled(False)
            return

        valid_count = 0
        invalid_count = 0
        temp_scraper = FourChanScraper()

        for url in urls:
            parsed_url = temp_scraper.parse_url(url)
            logger.info(f"Validating URL: {url}")
            logger.info(f"Parsed URL: {parsed_url}")
            if parsed_url:
                valid_count += 1
                logger.info(f"Valid URL: {url}")
            else:
                invalid_count += 1
                logger.warning(f"Invalid URL: {url}")

        logger.info(
            f"Validation complete: {valid_count} valid, {invalid_count} invalid"
        )

        if valid_count > 0:
            self.start_cancel_btn.setEnabled(True)
        else:
            self.start_cancel_btn.setEnabled(False)

    def handle_start_cancel_click(self):
        """Handles clicks on the main button, either starting or cancelling."""
        if self.download_thread and self.download_thread.isRunning():
            self.cancel_download()
        else:
            self.start_download()

    def start_download(self):
        """Start the download process for multiple URLs."""
        if not self.start_cancel_btn.isEnabled():
            return

        text = self.url_input.toPlainText().strip()
        urls = [url.strip() for url in text.split("\n") if url.strip()]
        if not urls:
            QMessageBox.critical(self, "Error", "No URLs provided")
            return

        # Check if download folder is set, if not prompt user
        if self.scraper.download_dir is None:
            folder = QFileDialog.getExistingDirectory(
                self,
                "Choose Download Folder",
                str(Path.home()),
                QFileDialog.Option.ShowDirsOnly,
            )

            if not folder:
                self.add_log_message("❌ Download cancelled - no folder selected")
                return

            self.scraper.download_dir = Path(folder)
            self.scraper.download_dir.mkdir(parents=True, exist_ok=True)
            self.add_log_message(f"📁 Download folder set to: {folder}")
            self.status_bar.showMessage(f"Download folder: {folder}")

        # Parse and validate URLs (strip numbering if present)
        parsed_urls = []
        for url in urls:
            # Strip numbering like "1. " from the beginning
            clean_url = re.sub(r"^\d+\.\s*", "", url.strip())
            parsed = self.scraper.parse_url(clean_url)
            if parsed:
                parsed_urls.append(parsed)
            else:
                self.add_log_message(f"⚠️ Skipping invalid URL: {clean_url}")

        if not parsed_urls:
            QMessageBox.critical(self, "Error", "No valid URLs found")
            return

        self.download_thread = QThread()
        self.download_worker = MultiUrlDownloadWorker(self.scraper, parsed_urls)
        self.download_worker.moveToThread(self.download_thread)

        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.speed_update.connect(self.update_speed)
        self.download_worker.log_message.connect(self.add_log_message)
        self.download_worker.finished.connect(self.download_finished)
        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_thread.finished.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        self.download_thread.finished.connect(self.thread_cleanup)

        self.log_text.clear()
        self._update_ui_for_state("downloading")
        self.status_bar.showMessage(f"Downloading from {len(parsed_urls)} URLs...")
        self.download_thread.start()

    def cancel_download(self):
        """Cancel the current download."""
        if self.download_worker:
            self.download_worker.cancel()
            self.add_log_message("🛑 Cancelling download...")
            self.start_cancel_btn.setEnabled(False)

    def download_finished(self, stats: Dict):
        """Handle download completion. This should ONLY update the UI."""
        self._update_ui_for_state("idle")

        total, downloaded, size_mb, duplicates = (
            stats.get("total", 0),
            stats.get("downloaded", 0),
            stats.get("size_mb", 0),
            stats.get("duplicates", 0),
        )
        status_msg = f"Complete: {downloaded}/{total} files ({size_mb:.1f}MB)"
        if duplicates > 0:
            status_msg += f" | {duplicates} duplicates skipped"
        self.status_bar.showMessage(status_msg if total > 0 else "No files found")

    def thread_cleanup(self):
        """Safely nullify thread and worker references after the thread has finished."""
        logger.info("QThread has finished, cleaning up references.")
        self.download_thread = None
        self.download_worker = None

    def toggle_pause_resume(self):
        """Toggle pause/resume state."""
        if self.download_worker:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.download_worker.pause()
                self.add_log_message("⏸️ Downloads paused")
                self._update_ui_for_state("paused")
            else:
                self.download_worker.resume()
                self.add_log_message("▶️ Downloads resumed")
                self._update_ui_for_state("downloading")

    def _update_ui_for_state(self, state: str):
        """Update the entire UI based on the application state."""
        if state == "idle":
            self.start_cancel_btn.setText("🚀 Start Download")
            self.start_cancel_btn.setObjectName("startBtn")
            self.pause_resume_btn.setVisible(False)
            self.validate_urls()
            self.speed_label.setText("Speed: 0.0 MB/s")
        elif state == "downloading":
            self.start_cancel_btn.setText("🛑 Cancel")
            self.start_cancel_btn.setObjectName("cancelBtn")
            self.start_cancel_btn.setEnabled(True)
            self.pause_resume_btn.setText("⏸️ Pause")
            self.pause_resume_btn.setVisible(True)
            self.is_paused = False
        elif state == "paused":
            self.pause_resume_btn.setText("▶️ Resume")

        self.start_cancel_btn.style().unpolish(self.start_cancel_btn)
        self.start_cancel_btn.style().polish(self.start_cancel_btn)

    def _update_url_status(self, text: str, state: str):
        """Update the URL status label with appropriate text and color."""
        colors = {
            "valid": "#4a9eff",
            "invalid": "#f44336",
            "partial": "#FF9800",
            "idle": "#888888",
        }
        color = colors.get(state, "#888888")
        self.status_bar.showMessage(text)
        self.status_bar.setStyleSheet(
            f"QStatusBar {{ color: {color}; font-size: 14px; font-weight: 600; padding: 8px 0; }}"
        )

    def update_progress(
        self,
        current: int,
        total: int,
        filename: str,
        speed: float,
        thread_name: str = "",
        thread_index: int = 0,
    ):
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
            if thread_name and thread_index > 0:
                self.progress_label.setText(
                    f"Progress: {current}/{total} files - [{thread_index}] {thread_name} - {filename}"
                )
            else:
                self.progress_label.setText(
                    f"Progress: {current}/{total} files - {filename}"
                )

    def update_speed(self, speed: float):
        self.speed_label.setText(f"Speed: {speed:.1f} MB/s")

    def add_log_message(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        # Update stats after each log message
        self.update_download_stats()

    def update_download_stats(self):
        """Update folder, file, and size statistics using macOS du command."""
        try:
            if (
                self.scraper.download_dir is None
                or not self.scraper.download_dir.exists()
            ):
                self.folders_label.setText("Folders: 0")
                self.files_label.setText("Files: 0")
                self.size_label.setText("Size: 0 MB")
                return

            # Count folders (subdirectories only, not the root)
            folders = [d for d in self.scraper.download_dir.iterdir() if d.is_dir()]
            folder_count = len(folders)

            # Count files recursively
            file_count = sum(
                1 for _ in self.scraper.download_dir.rglob("*") if _.is_file()
            )

            # Get size using macOS du command (more accurate)
            try:
                result = subprocess.run(
                    ["du", "-sk", str(self.scraper.download_dir)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    size_kb = int(result.stdout.split()[0])
                    size_mb = size_kb / 1024
                else:
                    # Fallback to Python calculation
                    size_mb = sum(
                        f.stat().st_size
                        for f in self.scraper.download_dir.rglob("*")
                        if f.is_file()
                    ) / (1024 * 1024)
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
                # Fallback to Python calculation
                size_mb = sum(
                    f.stat().st_size
                    for f in self.scraper.download_dir.rglob("*")
                    if f.is_file()
                ) / (1024 * 1024)

            # Update labels
            self.folders_label.setText(f"Folders: {folder_count}")
            self.files_label.setText(f"Files: {file_count}")
            self.size_label.setText(f"Size: {size_mb:.1f} MB")

        except Exception as e:
            logger.warning(f"Could not update download stats: {e}")

    def paste_from_clipboard(self):
        text = QApplication.clipboard().text().strip()
        if text and ("4chan.org" in text or "boards.4chan.org" in text):
            urls = re.findall(r"https?://[^\s]+", text)
            valid_urls = [
                url for url in urls if "boards.4chan.org" in url or "4chan.org" in url
            ]
            if valid_urls:
                # Always number the URLs starting from 1
                numbered_urls = [f"{i+1}. {url}" for i, url in enumerate(valid_urls)]
                self.url_input.setPlainText("\n".join(numbered_urls))

                # Move cursor to the end and add a new line
                cursor = self.url_input.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText("\n")
                self.url_input.setTextCursor(cursor)
                self._scroll_url_input_to_end()

                self.validate_urls()  # Trigger validation after paste

    def cancel_or_close(self):
        if self.download_thread and self.download_thread.isRunning():
            self.cancel_download()
        else:
            self.close()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        text = event.mimeData().text().strip()
        urls = re.findall(r"https?://[^\s]+", text)
        valid_urls = [
            url for url in urls if "boards.4chan.org" in url or "4chan.org" in url
        ]
        if valid_urls:
            numbered_urls = [f"{i+1}. {url}" for i, url in enumerate(valid_urls)]
            self.url_input.setPlainText("\n".join(numbered_urls))
            self._scroll_url_input_to_end()
            self.validate_urls()  # Trigger validation after drop

    def _scroll_url_input_to_end(self):
        """Scroll URL input to the newest entry so users can see recent additions."""
        # Use QTimer to ensure scrollbar maximum is calculated after text layout
        QTimer.singleShot(0, self._do_scroll_to_end)

    def _do_scroll_to_end(self):
        """Actually perform the scroll to end operation."""
        cursor = self.url_input.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.url_input.setTextCursor(cursor)
        self.url_input.ensureCursorVisible()
        scrollbar = self.url_input.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("4Charm")
    app.setApplicationVersion("3.0.0")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
