"""Behavioral tests for download workers."""

from __future__ import annotations

from typing import cast

from four_charm.core.scraper import FourChanScraper
from four_charm.gui import workers


class _FakeMutex:
    def __init__(self) -> None:
        self.lock_calls = 0
        self.unlock_calls = 0

    def lock(self) -> None:
        self.lock_calls += 1

    def unlock(self) -> None:
        self.unlock_calls += 1


class _FakeScraper:
    def __init__(self) -> None:
        self.stats = {
            "total": 0,
            "downloaded": 0,
            "failed": 0,
            "skipped": 0,
            "size_mb": 20.0,
            "download_speed": 0.0,
            "start_time": 100.0,
            "duplicates": 0,
            "current_speed": 0.0,
        }
        self.stats_mutex = _FakeMutex()
        self.cancel_calls = 0
        self.pause_calls = 0
        self.resume_calls = 0
        self.catalog_calls: list[tuple[str, int]] = []
        self.thread_calls: list[tuple[str, str]] = []

    def cancel_downloads(self) -> None:
        self.cancel_calls += 1

    def pause_downloads(self) -> None:
        self.pause_calls += 1

    def resume_downloads(self) -> None:
        self.resume_calls += 1

    def scrape_thread(self, board: str, thread_id: str):
        self.thread_calls.append((board, thread_id))
        return [object()], "Thread: Bad / Name"

    def scrape_catalog(self, board: str, limit: int):
        self.catalog_calls.append((board, limit))
        return []

    def build_thread_folder_name(
        self, thread_title: str, thread_id: str, board: str
    ) -> str:
        return f"{board}-{thread_id}-thread-folder"

    def build_session_base_name(self, parsed_url: dict) -> str:
        return f"{parsed_url['board']}-{parsed_url['type']}"


def test_workers_share_speed_calculation_and_controls(monkeypatch) -> None:
    """Both workers should delegate controls and compute speed consistently."""
    monkeypatch.setattr(workers.time, "time", lambda: 110.0)
    scraper = _FakeScraper()
    typed_scraper = cast(FourChanScraper, scraper)

    single = workers.DownloadWorker(typed_scraper, {"board": "g", "type": "catalog"})
    multi = workers.MultiUrlDownloadWorker(typed_scraper, [])

    assert single._calculate_average_speed() == 2.0
    assert multi._calculate_average_speed() == 2.0
    assert scraper.stats_mutex.lock_calls == 2
    assert scraper.stats_mutex.unlock_calls == 2

    single.cancel()
    single.pause()
    single.resume()
    multi.cancel()
    multi.pause()
    multi.resume()

    assert scraper.cancel_calls == 2
    assert scraper.pause_calls == 2
    assert scraper.resume_calls == 2


def test_build_url_task_uses_thread_title_folder_when_requested() -> None:
    scraper = _FakeScraper()
    worker = workers.MultiUrlDownloadWorker(cast(FourChanScraper, scraper), [])

    task = worker._build_url_task(
        {"board": "g", "type": "thread", "thread_id": "123"},
        url_index=2,
        use_thread_title_folder=True,
    )

    assert scraper.thread_calls == [("g", "123")]
    assert task["folder_name"] == "g-123-thread-folder"
    assert task["thread_title"] == "Thread: Bad / Name"
    assert task["url_index"] == 2
    assert len(task["media_files"]) == 1


def test_build_url_task_uses_catalog_limits_for_catalog_and_board() -> None:
    scraper = _FakeScraper()
    worker = workers.DownloadWorker(
        cast(FourChanScraper, scraper), {"board": "g", "type": "catalog"}
    )

    catalog_task = worker._build_url_task(
        {"board": "g", "type": "catalog"},
        url_index=0,
        use_thread_title_folder=False,
    )
    board_task = worker._build_url_task(
        {"board": "wsg", "type": "board"},
        url_index=1,
        use_thread_title_folder=False,
    )

    assert scraper.catalog_calls == [("g", 10), ("wsg", 5)]
    assert catalog_task["folder_name"] == "g-catalog"
    assert catalog_task["thread_title"] == "g catalog"
    assert board_task["folder_name"] == "wsg-board"
    assert board_task["thread_title"] == "wsg board"


def test_download_worker_finishes_when_no_media_found() -> None:
    scraper = _FakeScraper()
    worker = workers.DownloadWorker(
        cast(FourChanScraper, scraper), {"board": "g", "type": "catalog"}
    )
    log_messages: list[str] = []
    finished_payloads: list[dict] = []
    worker.log_message.connect(log_messages.append)
    worker.finished.connect(finished_payloads.append)

    worker.run()

    assert "❌ No media files found!" in log_messages
    assert finished_payloads == [scraper.stats]


def test_multi_url_worker_continues_after_scrape_failure() -> None:
    scraper = _FakeScraper()
    worker = workers.MultiUrlDownloadWorker(
        cast(FourChanScraper, scraper),
        [
            {"board": "g", "type": "thread", "thread_id": "1"},
            {"board": "wsg", "type": "thread", "thread_id": "2"},
        ],
    )
    log_messages: list[str] = []

    def flaky_scrape(board: str, thread_id: str):
        if board == "g":
            raise RuntimeError("network down")
        scraper.thread_calls.append((board, thread_id))
        return [object()], "Second thread"

    scraper.scrape_thread = flaky_scrape  # type: ignore[method-assign]
    worker.log_message.connect(log_messages.append)

    worker.run()

    assert any("Failed to process /g/thread/1" in message for message in log_messages)
    assert scraper.thread_calls == [("wsg", "2")]


def test_multi_url_worker_reports_empty_sources() -> None:
    scraper = _FakeScraper()
    worker = workers.MultiUrlDownloadWorker(
        cast(FourChanScraper, scraper),
        [
            {"board": "g", "type": "catalog"},
            {"board": "wsg", "type": "board"},
        ],
    )
    log_messages: list[str] = []
    finished_payloads: list[dict] = []
    worker.log_message.connect(log_messages.append)
    worker.finished.connect(finished_payloads.append)

    worker.run()

    assert "⚠️ [1/2] No media found for 'g catalog'" in log_messages
    assert "⚠️ [2/2] No media found for 'wsg board'" in log_messages
    assert "❌ No media files found in any URLs!" in log_messages
    assert finished_payloads == [scraper.stats]
