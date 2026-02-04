import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QObject, Signal

from four_charm.config import Config
from four_charm.core.scraper import FourChanScraper


logger = logging.getLogger("4Charm")


class DownloadWorker(QObject):
    """Enhanced worker thread for concurrent downloads."""

    progress = Signal(int, int, str, float, str, int)
    log_message = Signal(str)
    finished = Signal(dict)
    speed_update = Signal(float)

    def __init__(self, scraper: FourChanScraper, parsed_url: dict):
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
            error_msg = f"💥 Error: {e}"
            self.log_message.emit(error_msg)
            logger.error(f"DownloadWorker error: {traceback.format_exc()}")
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

    def __init__(self, scraper: FourChanScraper, parsed_urls: list[dict]):
        super().__init__()
        self.scraper = scraper
        self.parsed_urls = parsed_urls

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
                        f"📁 [{i + 1}/{len(self.parsed_urls)}] Found {len(media_files)} files in '{folder_name}'"
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
                        f"📁 [{i + 1}/{len(self.parsed_urls)}] Found {len(media_files)} files in '{folder_name}'"
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
                        f"📁 [{i + 1}/{len(self.parsed_urls)}] Found {len(media_files)} files in '{folder_name}'"
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
                                f"✅ [{task['url_index'] + 1}] {media_file.filename}{speed_info}"
                            )
                        else:
                            self.log_message.emit(
                                f"❌ [{task['url_index'] + 1}] Failed: {media_file.filename}"
                            )
                    except Exception as e:
                        self.log_message.emit(
                            f"❌ [{task['url_index'] + 1}] Error downloading {media_file.filename}: {e}"
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
            error_msg = f"💥 Error: {e}"
            self.log_message.emit(error_msg)
            logger.error(f"MultiUrlDownloadWorker error: {traceback.format_exc()}")
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
