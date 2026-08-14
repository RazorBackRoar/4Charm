"""Tests for DownloadQueue lifecycle used by the scraper download pipeline."""

from four_charm.core.models import DownloadQueue


def test_download_queue_tracks_active_complete_and_failed() -> None:
    queue = DownloadQueue()
    url_a = "https://i.4cdn.org/g/1.jpg"
    url_b = "https://i.4cdn.org/g/2.jpg"

    queue.add_url(url_a)
    queue.add_url(url_b)
    assert queue.get_stats() == {
        "queued": 2,
        "active": 0,
        "completed": 0,
        "failed": 0,
        "total": 2,
    }

    queue.start_download(url_a)
    assert queue.get_stats()["queued"] == 1
    assert queue.get_stats()["active"] == 1

    queue.complete_download(url_a)
    assert url_a in queue.completed
    assert queue.get_stats()["completed"] == 1
    assert queue.get_stats()["active"] == 0

    queue.start_download(url_b)
    queue.fail_download(url_b, Exception("timeout"))
    assert url_b in queue.failed
    assert queue.history[-1]["status"] == "failed"
    assert "timeout" in queue.history[-1]["error"]


def test_download_queue_ignores_duplicate_adds() -> None:
    queue = DownloadQueue()
    url = "https://i.4cdn.org/g/1.jpg"

    queue.add_url(url)
    queue.add_url(url)
    queue.start_download(url)
    queue.add_url(url)

    assert queue.get_stats()["queued"] == 0
    assert queue.get_stats()["active"] == 1
    assert queue.get_stats()["total"] == 1


def test_download_queue_clear_resets_state() -> None:
    queue = DownloadQueue()
    url = "https://i.4cdn.org/g/1.jpg"

    queue.add_url(url)
    queue.start_download(url)
    queue.complete_download(url)
    queue.clear_completed()

    assert queue.completed == []
    assert queue.failed == []

    queue.add_url(url)
    queue.clear_all()
    assert queue.get_stats()["total"] == 0
    assert queue.history == []

