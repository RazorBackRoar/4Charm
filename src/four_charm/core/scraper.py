import logging
import re
import shutil
import time
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

import requests
from PySide6.QtCore import QMutex

import four_charm.config as config
from four_charm.core.bandwidth import BandwidthMonitor
from four_charm.core.chunking import ChunkSelector
from four_charm.core.dedup import DedupTracker
from four_charm.core.error_format import ErrorFormatter
from four_charm.core.models import DownloadQueue, MediaFile
from four_charm.core.paths import (
    PathBuilder,
    sanitize_filename,
    sanitize_folder_component,
)
from four_charm.core.retry import RetryPolicy
from four_charm.core.urls import is_allowed_4chan_host, normalize_host
from four_charm.transport.api import BoardApi, LiveBoardApi
from four_charm.transport.session import create_session, safe_get


# Re-export for backward compatibility with imports like
# ``from four_charm.core.scraper import _rc_sanitize_filename``.
def _rc_sanitize_filename(name: str, replacement: str = "_") -> str:
    """Sanitize download filenames via razorcore (keeps 4Charm max length)."""
    return sanitize_filename(name, replacement=replacement)


# Re-export ``sanitize_folder_component`` as ``_sanitize_folder_component``
# for tests that historically imported the private method off the class.
_sanitize_folder_component = sanitize_folder_component


# Re-export so tests that monkeypatch ``four_charm.core.scraper.safe_get``
# keep working when the scraper delegates to a BoardApi.
__all__ = [
    "FourChanScraper",
    "_rc_sanitize_filename",
    "_sanitize_folder_component",
    "safe_get",
    "PathBuilder",
    "BoardApi",
    "LiveBoardApi",
]


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

    def __init__(self, board_api: BoardApi | None = None):
        # Don't set a default folder - let user choose on first download
        self._path_builder = PathBuilder()
        self.session = create_session()
        self._board_api: BoardApi = board_api or LiveBoardApi(self.session)
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
        self.dedup = DedupTracker()
        self.paused = False
        self.cancelled = False
        self.stats_mutex = QMutex()
        self._retry_policy = RetryPolicy()
        self._chunk_selector = ChunkSelector()
        self._error_formatter = ErrorFormatter()
        self.download_queue = DownloadQueue()
        self.bandwidth_monitor = BandwidthMonitor(config.BANDWIDTH_WINDOW_SECONDS)

    # ------------------------------------------------------------------
    # Legacy attribute mirrors for the rate-limit delay.
    #
    # ``current_delay`` was a public attribute that workers and tests read
    # directly. The new owner is ``RetryPolicy``; we mirror it for back
    # compatibility but new code should reach for ``self._retry_policy``.
    # ------------------------------------------------------------------
    @property
    def current_delay(self) -> float:
        return self._retry_policy.current_delay

    @current_delay.setter
    def current_delay(self, value: float) -> None:
        self._retry_policy.current_delay = value

    @property
    def download_dir(self) -> Path | None:
        """Active download root (mirrored into the internal PathBuilder)."""
        return self._path_builder.download_dir

    @download_dir.setter
    def download_dir(self, value: Path | None) -> None:
        self._path_builder.set_download_dir(value) if value is not None else setattr(
            self._path_builder, "download_dir", None
        )

    # ------------------------------------------------------------------
    # Path-building delegators
    #
    # The real logic lives in ``core.paths.PathBuilder``. The methods
    # below are kept as thin delegators so the existing test surface
    # (``test_scraper_utils``, ``test_cancel_reset``) keeps working
    # while the seam to razorcore stays at one location.
    # ------------------------------------------------------------------
    def _assert_within_download_dir(self, target: Path) -> Path:
        return self._path_builder.within_download_dir(target)

    def _prepare_download_path(
        self, media_file: MediaFile, url_folder_name: str | None
    ) -> tuple[Path, Path]:
        return self._path_builder.build(media_file, url_folder_name)

    def _sanitize_folder_component(self, name: str) -> str:
        return sanitize_folder_component(name)

    def build_session_base_name(self, parsed_url: dict) -> str:
        return self._path_builder.session_base_name(parsed_url)

    def build_thread_folder_name(
        self, thread_title: str | None, thread_id: str, board: str
    ) -> str:
        return self._path_builder.thread_folder_name(thread_title, thread_id, board)

    # ------------------------------------------------------------------
    # Retry / chunk / error delegators
    #
    # The real logic lives in ``core.retry.RetryPolicy``,
    # ``core.chunking.ChunkSelector`` and ``core.error_format.ErrorFormatter``.
    # These methods are thin delegators so the existing test surface
    # (``test_retry_logic``, ``test_md5_verification``) keeps working
    # while the math/formatting live at one location each.
    # ------------------------------------------------------------------
    def calculate_retry_delay(
        self, attempt: int, base_delay: float | None = None
    ) -> float:
        return self._retry_policy.calculate_retry_delay(attempt, base_delay)

    def adaptive_delay(self, success: bool = True) -> None:
        self._retry_policy.adaptive_delay(success)

    def select_chunk_size(self, file_size: int) -> int:
        return self._chunk_selector.select_chunk_size(file_size)

    def format_error_message(self, error: Exception, context: dict) -> str:
        return self._error_formatter.format_error_message(error, context)

    def handle_network_error(
        self,
        error: Exception,
        url: str,
        context: str = "",
        filename: str = "",
    ) -> dict:
        """Classify ``error`` and update rate-limit delay on 429.

        The classifier itself is ``ErrorFormatter.classify``; this wrapper
        keeps the historic behavior of bumping ``current_delay`` for a 429
        response and sleeping before the caller retries.
        """
        # Compute a 2x delay in advance so the message can include it.
        retry_delay = self._retry_policy.current_delay * 2
        info = self._error_formatter.classify(
            error,
            url=url,
            context=context,
            filename=filename,
            retry_delay_for_rate_limit=retry_delay,
        )
        if info.get("category") == "rate_limited":
            self._retry_policy.current_delay = min(
                self._retry_policy.max_delay,
                self._retry_policy.current_delay * 2,
            )
            time.sleep(self._retry_policy.current_delay)
        else:
            self._retry_policy.adaptive_delay(success=False)
        return info

    def _check_existing_file(self, file_path: Path, media_file: MediaFile) -> bool:
        """Check for existing complete file and handle duplicates."""
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False

        try:
            file_hash = media_file.calculate_hash(file_path)

            if self.dedup.check_and_register(file_hash):
                # Hash already seen — duplicate of a file downloaded this session
                media_file.skip_reason = "duplicate"
                self.stats_mutex.lock()
                try:
                    self.stats["duplicates"] += 1
                finally:
                    self.stats_mutex.unlock()
                self.download_queue.complete_download(media_file.url)
                return True

        except (OSError, PermissionError) as e:
            logger.warning(f"Hash calculation failed for {file_path}: {e}")
            # Continue with download instead of treating as existing file
            return False

        media_file.skip_reason = "skipped"
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

    def _mark_download_cancelled(
        self, media_url: str, file_path: Path | None = None
    ) -> bool:
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
            f"Download attempt {attempt + 1}/{config.MAX_RETRIES} failed for {media_file.filename} "
            f"(URL: {media_file.url}): {error}"
        )
        is_last_attempt = attempt == config.MAX_RETRIES - 1
        if is_last_attempt:
            logger.error(
                f"Download failed permanently for {media_file.filename} "
                f"(URL: {media_file.url}): {error}"
            )
            self._record_failed_download(media_file.url, error)
            return False

        # Use exponential backoff with jitter
        delay = self.calculate_retry_delay(attempt)
        logger.info(f"Retrying {media_file.filename} after {delay:.1f}s delay")
        time.sleep(delay)
        return True

    def verify_download(self, file_path: Path, media_file: MediaFile) -> bool:
        """Verify downloaded file integrity using MD5 checksum and size.

        Args:
            file_path: Path to downloaded file
            media_file: MediaFile with expected checksums

        Returns:
            True if verification passed, False otherwise
        """
        import hashlib

        # Check file exists and has content
        if not file_path.exists() or file_path.stat().st_size == 0:
            logger.error(f"Verification failed: {file_path} is empty or missing")
            return False

        # Verify size if available
        if media_file.size and media_file.size > 0:
            actual_size = file_path.stat().st_size
            if actual_size != media_file.size:
                logger.error(
                    f"Size mismatch for {media_file.filename}: "
                    f"expected {media_file.size}, got {actual_size}"
                )
                return False

        # Verify MD5 if available
        if media_file.expected_md5:
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    md5_hash.update(chunk)

            actual_md5 = md5_hash.hexdigest()
            # 4chan API returns base64-encoded MD5, we need to decode it
            import base64

            try:
                expected_md5_hex = base64.b64decode(media_file.expected_md5).hex()
            except Exception:
                # If decoding fails, assume it's already hex
                expected_md5_hex = media_file.expected_md5

            if actual_md5 != expected_md5_hex:
                logger.error(
                    f"MD5 mismatch for {media_file.filename}: "
                    f"expected {expected_md5_hex}, got {actual_md5}"
                )
                return False

            logger.info(f"MD5 verified for {media_file.filename}")

        media_file.verified = True
        return True

    def check_disk_space(self, required_mb: float = 0) -> bool:
        """Check if sufficient disk space is available."""
        if self.download_dir is None:
            return False
        try:
            free_space_bytes = shutil.disk_usage(self.download_dir).free
            free_space_mb = free_space_bytes / (1024 * 1024)
            return free_space_mb > (config.MIN_FREE_SPACE_MB + required_mb)
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            return True

    def parse_url(self, url: str) -> dict | None:
        """Parse 4chan URL to extract board, thread, catalog, or direct media info."""
        try:
            url = url.strip()
            if not url:
                return None
            if not url.startswith("http"):
                url = "https://" + url
            parsed = urlparse(url)
            hostname = normalize_host(parsed.hostname)
            if not is_allowed_4chan_host(hostname):
                return None

            if hostname == "i.4cdn.org":
                path_parts = [p for p in parsed.path.split("/") if p]
                if len(path_parts) < 2:
                    return None
                board = path_parts[0]
                media_filename = path_parts[1].split("#")[0]
                extension = Path(media_filename).suffix.lower()
                if extension not in config.MEDIA_EXTENSIONS:
                    return None
                return {
                    "board": board,
                    "type": "media",
                    "thread_id": None,
                    "media_filename": media_filename,
                    "media_url": url,
                }

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

    @staticmethod
    def _extract_thread_title(posts: list[dict]) -> str | None:
        """Extract thread title from the OP post. Returns None if no usable title."""
        if not posts:
            return None
        op = posts[0]
        if "sub" in op and op["sub"]:
            return op["sub"]
        if "com" in op and op["com"]:
            text = re.sub(r"<[^>]+>", "", op["com"]).strip()
            if text:
                return re.sub(r"\s+", " ", text[:60]).strip()
        return None

    def get_thread_data(self, board: str, thread_id: str) -> dict | None:
        """Fetch thread JSON data from 4chan API with adaptive rate limiting."""
        self.adaptive_delay()  # Adaptive rate limiting
        api_url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
        try:
            response = self._board_api.fetch_thread(board, thread_id)
            response.raise_for_status()
            thread_data = response.json()
            thread_data["_thread_title"] = self._extract_thread_title(
                thread_data.get("posts", [])
            )
            self.adaptive_delay(success=True)  # Success, reduce delay
            return thread_data
        except Exception as e:
            error_info = self.handle_network_error(e, api_url, "getting thread data")
            if error_info.get("category") == "rate_limited":
                # Retry once after rate limit handling
                try:
                    time.sleep(config.RETRY_DELAY)
                    response = self._board_api.fetch_thread(board, thread_id)
                    response.raise_for_status()
                    thread_data = response.json()
                    thread_data["_thread_title"] = self._extract_thread_title(
                        thread_data.get("posts", [])
                    )
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
            response = self._board_api.fetch_catalog(board)
            response.raise_for_status()
            catalog_data = response.json()
            self.adaptive_delay(success=True)  # Success, reduce delay
            return catalog_data
        except Exception as e:
            error_info = self.handle_network_error(e, api_url, "getting catalog data")
            if error_info.get("category") == "rate_limited":
                # Retry once after rate limit handling
                try:
                    time.sleep(config.RETRY_DELAY)
                    response = self._board_api.fetch_catalog(board)
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
                if ext in config.MEDIA_EXTENSIONS:
                    filename = f"{post['tim']}{ext}"
                    original_name = post.get("filename", "unnamed") + ext
                    # i.4cdn.org serves original, full-quality files (same as browsers download)
                    media_url = f"https://i.4cdn.org/{board}/{filename}"
                    safe_filename = _rc_sanitize_filename(original_name)
                    media_file = MediaFile(
                        url=media_url,
                        filename=safe_filename,
                        board=board,
                        thread_id=thread_id,
                    )
                    # Store file size from API if available (for quality verification)
                    if "fsize" in post:
                        media_file.size = post["fsize"]
                    # Store MD5 checksum from API if available (for integrity verification)
                    if "md5" in post:
                        media_file.expected_md5 = post["md5"]
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
                    time.sleep(config.CATALOG_SCRAPE_DELAY)
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

        for attempt in range(config.MAX_RETRIES):
            try:
                file_path, _save_dir = self._prepare_download_path(
                    media_file, url_folder_name
                )

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
                response = self._board_api.stream_range(
                    media_file.url,
                    headers=headers,
                    timeout=config.DOWNLOAD_TIMEOUT,
                )

                mode, total_size = self._handle_download_response(
                    response, file_path, existing_size
                )

                # Select optimal chunk size based on file size
                chunk_size = self.select_chunk_size(total_size)
                logger.debug(
                    f"Using {chunk_size} byte chunks for {media_file.filename} ({total_size} bytes)"
                )

                downloaded_size = existing_size

                with open(file_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if not self._ensure_active_download(media_file.url, file_path):
                            return False

                        if not chunk:
                            continue

                        f.write(chunk)
                        chunk_len = len(chunk)
                        downloaded_size += chunk_len

                        # Record bandwidth progress
                        self.bandwidth_monitor.record_progress(chunk_len)

                        elapsed = time.time() - media_file.start_time
                        if elapsed > 0:
                            media_file.download_speed = (
                                downloaded_size / elapsed / 1024 / 1024
                            )

                        if progress_callback and total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            current_speed = self.bandwidth_monitor.get_current_speed()
                            bytes_remaining = total_size - downloaded_size
                            eta = self.bandwidth_monitor.calculate_eta(bytes_remaining)
                            # Call with backward-compatible signature (speed only, eta as optional 3rd param)
                            try:
                                progress_callback(progress, current_speed, eta)
                            except TypeError:
                                # Fallback for old signature (progress, speed)
                                progress_callback(progress, current_speed)

                file_size = file_path.stat().st_size
                if file_size == 0:
                    file_path.unlink(missing_ok=True)
                    raise Exception("Downloaded file is empty")

                # Verify download integrity (MD5 and size check)
                if not self.verify_download(file_path, media_file):
                    logger.warning(
                        f"Verification failed for {media_file.filename}, deleting and retrying"
                    )
                    file_path.unlink(missing_ok=True)
                    raise Exception("Download verification failed")

                try:
                    media_file.hash = media_file.calculate_hash(file_path)
                    self.dedup.add(media_file.hash)
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

    def prepare_for_download(self) -> None:
        """Reset cancel/pause and per-run stats before a new download session.

        The scraper is shared across runs. ``cancel_downloads`` sets
        ``cancelled=True`` and must not permanently disable later Start clicks.
        """
        self.cancelled = False
        self.paused = False
        self.stats_mutex.lock()
        try:
            self.stats["total"] = 0
            self.stats["downloaded"] = 0
            self.stats["failed"] = 0
            self.stats["skipped"] = 0
            self.stats["size_mb"] = 0.0
            self.stats["download_speed"] = 0.0
            self.stats["start_time"] = None
            self.stats["duplicates"] = 0
            self.stats["current_speed"] = 0.0
        finally:
            self.stats_mutex.unlock()

    def pause_downloads(self):
        self.paused = True

    def resume_downloads(self):
        self.paused = False

    def cancel_downloads(self):
        self.cancelled = True
        self.paused = False
