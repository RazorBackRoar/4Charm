import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

import requests
from PySide6.QtCore import QMutex
from requests.adapters import HTTPAdapter

from four_charm.config import Config
from four_charm.core.models import DownloadQueue, MediaFile


logger = logging.getLogger("4Charm")


class ScraperStats(TypedDict):
    total: int
    downloaded: int
    failed: int
    skipped: int
    size_mb: float
    download_speed: float
    start_time: float | None
    duplicates: int
    current_speed: float


class FourChanScraper:
    """Enhanced scraper for 4chan media files with concurrent downloads."""

    def __init__(self):
        # Don't set a default folder - let user choose on first download
        self.download_dir: Path | None = None
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
        self.stats: ScraperStats = {
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

    def _prepare_download_path(
        self, media_file: MediaFile, url_folder_name: str | None
    ) -> tuple[Path, Path]:
        """Prepare download directory and file path."""
        if self.download_dir is None:
            raise ValueError("Download directory not set")

        if url_folder_name:
            thread_dir = self.download_dir / url_folder_name
        else:
            thread_dir = self.download_dir / "misc"
        thread_dir.mkdir(parents=True, exist_ok=True)

        if media_file.filename.lower().endswith(".webm"):
            save_dir = thread_dir / "WEBM"
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = thread_dir

        file_path = save_dir / media_file.filename
        return file_path, save_dir

    def _check_existing_file(self, file_path: Path, media_file: MediaFile) -> bool:
        """Check for existing complete file and handle duplicates."""
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False

        try:
            file_hash = media_file.calculate_hash(file_path)

            # Protect hash set access with mutex to prevent race conditions
            self.stats_mutex.lock()
            try:
                if file_hash in self.downloaded_hashes:
                    self.stats["duplicates"] += 1
                    self.download_queue.complete_download(media_file.url)
                    return True
                self.downloaded_hashes.add(file_hash)
            finally:
                self.stats_mutex.unlock()

        except (OSError, PermissionError) as e:
            logger.warning(f"Hash calculation failed for {file_path}: {e}")
            # Continue with download instead of treating as existing file
            return False

        self.stats_mutex.lock()
        try:
            self.stats["skipped"] += 1
        finally:
            self.stats_mutex.unlock()
        media_file.downloaded = True
        self.download_queue.complete_download(media_file.url)
        return True

    def _handle_download_response(
        self, response: requests.Response, file_path: Path, existing_size: int
    ) -> tuple[str, int]:
        """Handle HTTP response for download, return (file mode, total size)."""
        if response.status_code == 206:
            return "ab", int(response.headers.get("content-length", 0)) + existing_size
        elif response.status_code == 200:
            if file_path.exists():
                file_path.unlink()
            return "wb", int(response.headers.get("content-length", 0))
        else:
            # This will raise an exception and not return
            response.raise_for_status()
            # Add a fallback to satisfy type checker (though this should never be reached)
            return "wb", 0

    def _update_stats_on_success(self, file_path: Path, media_file: MediaFile):
        """Update stats after successful download."""
        file_size = file_path.stat().st_size
        media_file.size = file_size
        media_file.downloaded = True
        self.stats_mutex.lock()
        try:
            self.stats["downloaded"] += 1
            self.stats["size_mb"] += file_size / (1024 * 1024)
            self.stats["current_speed"] = media_file.download_speed
        finally:
            self.stats_mutex.unlock()

    def _mark_download_cancelled(self, media_url: str, file_path: Path | None = None) -> bool:
        """Handle cancellation by cleaning up and marking queue item failed."""
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)
        self.download_queue.fail_download(media_url, Exception("Cancelled"))
        return False

    def _ensure_active_download(
        self, media_url: str, file_path: Path | None = None
    ) -> bool:
        """Return False when download is canceled while handling pause state."""
        if self.cancelled:
            return self._mark_download_cancelled(media_url, file_path)

        while self.paused:
            time.sleep(0.1)
            if self.cancelled:
                return self._mark_download_cancelled(media_url, file_path)
        return True

    def _build_resume_headers(
        self, file_path: Path, filename: str
    ) -> tuple[dict[str, str], int]:
        """Build HTTP range headers for resumable downloads."""
        headers: dict[str, str] = {}
        existing_size = 0
        if file_path.exists():
            existing_size = file_path.stat().st_size
            if existing_size > 0:
                headers["Range"] = f"bytes={existing_size}-"
                logger.info(f"Resuming {filename} from byte {existing_size}")
        return headers, existing_size

    def _record_failed_download(self, media_url: str, error: Exception) -> None:
        """Record failed download state and update failed stats."""
        self.stats_mutex.lock()
        try:
            self.stats["failed"] += 1
        finally:
            self.stats_mutex.unlock()
        self.download_queue.fail_download(media_url, error)

    def _handle_download_retry(
        self,
        media_file: MediaFile,
        attempt: int,
        error: Exception,
    ) -> bool:
        """Handle retry bookkeeping. Returns True when a retry should occur."""
        logger.warning(
            f"Download attempt {attempt + 1}/{Config.MAX_RETRIES} failed for {media_file.filename} "
            f"(URL: {media_file.url}): {error}"
        )
        is_last_attempt = attempt == Config.MAX_RETRIES - 1
        if is_last_attempt:
            logger.error(
                f"Download failed permanently for {media_file.filename} "
                f"(URL: {media_file.url}): {error}"
            )
            self._record_failed_download(media_file.url, error)
            return False

        time.sleep(2**attempt)
        return True

    def adaptive_delay(self, success=True):
        """Adaptive rate limiting based on success/failure."""
        if success:
            self.current_delay = max(Config.BASE_DELAY, self.current_delay / 1.1)
        else:
            self.current_delay = min(
                Config.MAX_DELAY, self.current_delay * Config.BACKOFF_MULTIPLIER
            )
        time.sleep(self.current_delay)

    def handle_network_error(self, error, url, context=""):
        """Handle different types of network errors with appropriate responses."""
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

    def build_session_base_name(self, parsed_url: dict) -> str:
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
        self, thread_title: str | None, thread_id: str, board: str
    ) -> str:
        """Build folder name for thread using title. Falls back to board-thread_id if no title."""
        if thread_title and thread_title.strip():
            # Sanitize the thread title for folder name
            folder_name = self._sanitize_folder_component(thread_title)

            # Truncate if too long (keep all words, just shorten if needed)
            if len(folder_name) > Config.MAX_FOLDER_NAME_LENGTH:
                folder_name = folder_name[: Config.MAX_FOLDER_NAME_LENGTH].rstrip("-_ ")
            # Only return if we have a valid title
            if folder_name:
                return folder_name

        # Fallback: use board-thread_id format if no title available
        return f"{board}-{thread_id}"

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

    def parse_url(self, url: str) -> dict | None:
        """Parse 4chan URL to extract board and thread info."""
        try:
            url = url.strip()
            if not url.startswith("http"):
                url = "https://" + url
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower()
            if hostname != "4chan.org" and not hostname.endswith(".4chan.org"):
                return None
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

    def get_thread_data(self, board: str, thread_id: str) -> dict | None:
        """Fetch thread JSON data from 4chan API with adaptive rate limiting."""
        self.adaptive_delay()  # Adaptive rate limiting
        api_url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
        try:
            response = self.session.get(api_url, timeout=Config.API_TIMEOUT)
            response.raise_for_status()
            thread_data = response.json()
            # Extract thread title from the first post (OP)
            posts = thread_data.get("posts", [])
            thread_title = None
            if posts:
                op = posts[0]
                # First try "sub" field (subject/title)
                if "sub" in op and op["sub"]:
                    thread_title = op["sub"]
                # Fallback to first part of comment if no subject
                elif "com" in op and op["com"]:
                    # Extract text from HTML comment, take first 60 chars
                    text = re.sub(r"<[^>]+>", "", op["com"])  # Remove HTML tags
                    text = text.strip()
                    if text:
                        # Use first 60 characters as title
                        thread_title = text[:60].strip()
                        # Remove newlines and extra spaces
                        thread_title = re.sub(r"\s+", " ", thread_title)
            thread_data["_thread_title"] = thread_title
            self.adaptive_delay(success=True)  # Success, reduce delay
            return thread_data
        except Exception as e:
            error_info = self.handle_network_error(e, api_url, "getting thread data")
            if error_info.get("category") == "rate_limited":
                # Retry once after rate limit handling
                try:
                    time.sleep(Config.RETRY_DELAY)
                    response = self.session.get(api_url, timeout=Config.API_TIMEOUT)
                    response.raise_for_status()
                    thread_data = response.json()
                    posts = thread_data.get("posts", [])
                    thread_title = None
                    if posts:
                        op = posts[0]
                        # First try "sub" field (subject/title)
                        if "sub" in op and op["sub"]:
                            thread_title = op["sub"]
                        # Fallback to first part of comment if no subject
                        elif "com" in op and op["com"]:
                            # Extract text from HTML comment, take first 60 chars
                            text = re.sub(r"<[^>]+>", "", op["com"])  # Remove HTML tags
                            text = text.strip()
                            if text:
                                # Use first 60 characters as title
                                thread_title = text[:60].strip()
                                # Remove newlines and extra spaces
                                thread_title = re.sub(r"\s+", " ", thread_title)
                    thread_data["_thread_title"] = thread_title
                    return thread_data
                except Exception as e2:
                    logger.error(f"Retry failed for {api_url}: {e2}")
                    return None
            return None

    def get_catalog_data(self, board: str) -> list | None:
        """Fetch catalog data from 4chan API with adaptive rate limiting."""
        self.adaptive_delay()  # Adaptive rate limiting
        api_url = f"https://a.4cdn.org/{board}/catalog.json"
        try:
            response = self.session.get(api_url, timeout=Config.API_TIMEOUT)
            response.raise_for_status()
            catalog_data = response.json()
            self.adaptive_delay(success=True)  # Success, reduce delay
            return catalog_data
        except Exception as e:
            error_info = self.handle_network_error(e, api_url, "getting catalog data")
            if error_info.get("category") == "rate_limited":
                # Retry once after rate limit handling
                try:
                    time.sleep(Config.RETRY_DELAY)
                    response = self.session.get(api_url, timeout=Config.API_TIMEOUT)
                    response.raise_for_status()
                    return response.json()
                except Exception as e2:
                    logger.error(f"Retry failed for {api_url}: {e2}")
                    return None
            return None

    def extract_media_from_posts(
        self, posts: list[dict], board: str, thread_id: str = ""
    ) -> list[MediaFile]:
        """Extract media files from posts. Downloads original, full-quality files from i.4cdn.org."""
        media_files = []
        for post in posts:
            if "tim" in post and "ext" in post:
                ext = post["ext"].lower()
                if ext in Config.MEDIA_EXTENSIONS:
                    filename = f"{post['tim']}{ext}"
                    original_name = post.get("filename", "unnamed") + ext
                    # i.4cdn.org serves original, full-quality files (same as browsers download)
                    media_url = f"https://i.4cdn.org/{board}/{filename}"
                    safe_filename = self.sanitize_filename(original_name)
                    media_file = MediaFile(
                        url=media_url,
                        filename=safe_filename,
                        board=board,
                        thread_id=thread_id,
                    )
                    # Store file size from API if available (for quality verification)
                    if "fsize" in post:
                        media_file.size = post["fsize"]
                    media_files.append(media_file)
        return media_files

    def scrape_thread(
        self, board: str, thread_id: str
    ) -> tuple[list[MediaFile], str | None]:
        """Get all media files from a specific thread."""
        logger.info(f"Scraping thread /{board}/{thread_id}")
        thread_data = self.get_thread_data(board, thread_id)
        if not thread_data:
            return [], None
        posts = thread_data.get("posts", [])
        thread_title = thread_data.get("_thread_title")
        media_files = self.extract_media_from_posts(posts, board, thread_id)
        return media_files, thread_title

    def scrape_catalog(self, board: str, max_threads: int = 10) -> list[MediaFile]:
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
                    time.sleep(Config.CATALOG_SCRAPE_DELAY)
        return media_files

    def download_file(
        self,
        media_file: MediaFile,
        url_folder_name: str | None = None,
        progress_callback=None,
    ) -> bool:
        """Enhanced download with progress tracking, duplicate detection, and resume capability."""
        if self.download_dir is None:
            logger.error("Download directory not set")
            return False

        self.download_queue.start_download(media_file.url)

        if not self._ensure_active_download(media_file.url):
            return False

        for attempt in range(Config.MAX_RETRIES):
            try:
                file_path, _save_dir = self._prepare_download_path(media_file, url_folder_name)

                if self._check_existing_file(file_path, media_file):
                    return True

                if not self.check_disk_space():
                    logger.error("Insufficient disk space")
                    self._record_failed_download(
                        media_file.url, Exception("Insufficient disk space")
                    )
                    return False

                headers, existing_size = self._build_resume_headers(
                    file_path, media_file.filename
                )

                media_file.start_time = time.time()
                response = self.session.get(
                    media_file.url,
                    headers=headers,
                    stream=True,
                    timeout=Config.DOWNLOAD_TIMEOUT,
                    allow_redirects=True,
                )

                mode, total_size = self._handle_download_response(
                    response, file_path, existing_size
                )

                downloaded_size = existing_size

                with open(file_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=Config.CHUNK_SIZE):
                        if not self._ensure_active_download(media_file.url, file_path):
                            return False

                        if not chunk:
                            continue

                        f.write(chunk)
                        downloaded_size += len(chunk)

                        elapsed = time.time() - media_file.start_time
                        if elapsed > 0:
                            media_file.download_speed = downloaded_size / elapsed / 1024 / 1024

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

                self._update_stats_on_success(file_path, media_file)
                self.download_queue.complete_download(media_file.url)
                return True

            except Exception as e:
                if not self._handle_download_retry(media_file, attempt, e):
                    return False

        self.download_queue.fail_download(
            media_file.url, Exception("Max retries exceeded")
        )
        return False

    def pause_downloads(self):
        self.paused = True

    def resume_downloads(self):
        self.paused = False

    def cancel_downloads(self):
        self.cancelled = True
        self.paused = False
