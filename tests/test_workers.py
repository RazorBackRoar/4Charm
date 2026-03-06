"""Behavioral tests for download workers."""

from __future__ import annotations

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
        self.stats = {"start_time": 100.0, "size_mb": 20.0}
        self.stats_mutex = _FakeMutex()
        self.cancel_calls = 0
        self.pause_calls = 0
        self.resume_calls = 0

    def cancel_downloads(self) -> None:
        self.cancel_calls += 1

    def pause_downloads(self) -> None:
        self.pause_calls += 1

    def resume_downloads(self) -> None:
        self.resume_calls += 1


def test_workers_share_speed_calculation_and_controls(monkeypatch) -> None:
    """Both workers should delegate controls and compute speed consistently."""
    monkeypatch.setattr(workers.time, "time", lambda: 110.0)
    scraper = _FakeScraper()

    single = workers.DownloadWorker(scraper, {"board": "g", "type": "catalog"})
    multi = workers.MultiUrlDownloadWorker(scraper, [])

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
