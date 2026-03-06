import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from PySide6.QtCore import QObject, Signal

from four_charm.config import Config
from four_charm.core.scraper import FourChanScraper


logger = logging.getLogger("4Charm")


class _BaseDownloadWorker(QObject):
    """Shared download worker behavior for single and multi-URL flows."""

    progress = Signal(int, int, str, float, str, int)
    log_message = Signal(str)
    finished = Signal(dict)
    speed_update = Signal(float)

    def __init__(self, scraper: FourChanScraper):
        super().__init__()
        self.scraper = scraper

    def run(self):
        """Run worker logic."""
        raise NotImplementedError

    def _build_url_task(
        self,
        parsed_url: dict[str, Any],
        *,
        url_index: int,
        use_thread_title_folder: bool,
    ) -> dict[str, Any]:
        """Scrape one parsed URL and normalize its download task metadata."""
        board = parsed_url["board"]
        url_type = parsed_url["type"]
        thread_id = parsed_url.get("thread_id")

        if url_type == "thread" and thread_id:
            media_files, thread_title = self.scraper.scrape_thread(board, thread_id)
            if use_thread_title_folder:
                folder_name = self.scraper.build_thread_folder_name(
                    thread_title, thread_id, board
                )
            else:
                folder_name = self.scraper.build_session_base_name(parsed_url)
            display_title = thread_title or f"Thread {thread_id}"
        elif url_type == "catalog":
            media_files = self.scraper.scrape_catalog(board, 10)
            folder_name = self.scraper.build_session_base_name(parsed_url)
            display_title = f"{board} catalog"
        else:
            media_files = self.scraper.scrape_catalog(board, 5)
            folder_name = self.scraper.build_session_base_name(parsed_url)
            display_title = f"{board} board"

        return {
            "parsed_url": parsed_url,
            "media_files": media_files,
            "folder_name": folder_name,
            "thread_title": display_title,
            "url_index": url_index,
        }

    def _download_all(
        self,
        downloads: list[tuple[Any, str, str, int]],
        total_files: int,
    ) -> None:
        """Submit and process all download futures for this worker."""
        completed = 0
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            future_to_file = {
                executor.submit(self.scraper.download_file, media_file, folder_name): (
                    media_file,
                    thread_title,
                    thread_index,
                )
                for media_file, folder_name, thread_title, thread_index in downloads
            }

            for future in as_completed(future_to_file):
                if self.scraper.cancelled:
                    self.log_message.emit("🛑 Download cancelled")
                    break

                media_file, thread_title, thread_index = future_to_file[future]
                completed += 1

                prefix = f"[{thread_index}] " if thread_index else ""
                try:
                    success = future.result()
                    if success:
                        speed_info = (
                            f" ({media_file.download_speed:.1f} MB/s)"
                            if media_file.download_speed > 0
                            else ""
                        )
                        self.log_message.emit(
                            f"✅ {prefix}{media_file.filename}{speed_info}"
                        )
                    else:
                        self.log_message.emit(
                            f"❌ {prefix}Failed: {media_file.filename}"
                        )
                except Exception as e:
                    self.log_message.emit(
                        f"❌ {prefix}Error downloading {media_file.filename}: {e}"
                    )

                avg_speed = self._calculate_average_speed()
                self.progress.emit(
                    completed,
                    total_files,
                    media_file.filename,
                    avg_speed,
                    thread_title,
                    thread_index,
                )
                self.speed_update.emit(avg_speed)

    def _emit_summary(self, source_count: int = 0) -> None:
        """Emit final download summary and completion signal."""
        stats = self.scraper.stats
        total_time = time.time() - (stats["start_time"] or time.time())
        avg_speed = stats["size_mb"] / total_time if total_time > 0 else 0
        source_segment = f" from {source_count} URLs" if source_count else ""

        self.log_message.emit(
            f"🎉 Complete! {stats['downloaded']}/{stats['total']} files "
            f"({stats['size_mb']:.1f}MB){source_segment} in {total_time:.1f}s - Avg: {avg_speed:.1f} MB/s"
        )
        if stats["duplicates"] > 0:
            self.log_message.emit(f"🔄 Skipped {stats['duplicates']} duplicate files")

        self.finished.emit(stats)

    def _handle_run_error(self, worker_name: str, error: Exception) -> None:
        """Emit the standard worker failure state."""
        error_msg = f"💥 Error: {error}"
        self.log_message.emit(error_msg)
        logger.error(f"{worker_name} error: {traceback.format_exc()}")
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


class DownloadWorker(_BaseDownloadWorker):
    """Enhanced worker thread for concurrent downloads."""

    def __init__(self, scraper: FourChanScraper, parsed_url: dict):
        super().__init__(scraper)
        self.parsed_url = parsed_url

    def run(self):
        """Enhanced concurrent download logic."""
        try:
            task = self._build_url_task(
                self.parsed_url,
                url_index=0,
                use_thread_title_folder=False,
            )
            media_files = task["media_files"]

            if not media_files:
                self.log_message.emit("❌ No media files found!")
                self.finished.emit(self.scraper.stats)
                return

            self.scraper.stats["total"] = len(media_files)
            self.scraper.stats["start_time"] = time.time()
            self.log_message.emit(f"📁 Found {len(media_files)} media files")

            downloads = [
                (media_file, task["folder_name"], "", 0) for media_file in media_files
            ]
            self._download_all(downloads, len(media_files))
            self._emit_summary()
        except Exception as e:
            self._handle_run_error("DownloadWorker", e)


class MultiUrlDownloadWorker(_BaseDownloadWorker):
    """Worker for concurrent downloads from multiple URLs."""

    def __init__(self, scraper: FourChanScraper, parsed_urls: list[dict]):
        super().__init__(scraper)
        self.parsed_urls = parsed_urls

    def run(self):
        """Run concurrent downloads from multiple URLs."""
        try:
            total_files = 0
            url_tasks: list[dict[str, Any]] = []

            # First pass: scrape all URLs to get media counts
            for i, parsed_url in enumerate(self.parsed_urls):
                task = self._build_url_task(
                    parsed_url,
                    url_index=i,
                    use_thread_title_folder=True,
                )
                url_tasks.append(task)
                media_files = task["media_files"]
                total_files += len(media_files)
                self.log_message.emit(
                    f"📁 [{i + 1}/{len(self.parsed_urls)}] Found {len(media_files)} files in '{task['folder_name']}'"
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

            downloads = [
                (
                    media_file,
                    task["folder_name"],
                    task["thread_title"],
                    task["url_index"] + 1,
                )
                for task in url_tasks
                for media_file in task["media_files"]
            ]
            self._download_all(downloads, total_files)
            self._emit_summary(source_count=len(url_tasks))
        except Exception as e:
            self._handle_run_error("MultiUrlDownloadWorker", e)
