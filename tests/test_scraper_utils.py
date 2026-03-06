"""Logic tests for FourChanScraper utilities."""

from pathlib import Path

from four_charm.config import Config
from four_charm.core.models import MediaFile
from four_charm.core.scraper import FourChanScraper


def test_parse_url_thread_and_catalog():
    """Parse thread, catalog, and invalid URLs."""
    scraper = FourChanScraper()

    thread = scraper.parse_url("https://boards.4chan.org/g/thread/123456789")
    catalog = scraper.parse_url("https://boards.4chan.org/g/catalog")
    invalid = scraper.parse_url("https://example.com/not-4chan")

    assert thread == {"board": "g", "type": "thread", "thread_id": "123456789"}
    assert catalog == {"board": "g", "type": "catalog", "thread_id": None}
    assert invalid is None


def test_parse_url_rejects_hostname_substring_spoof():
    """Reject hosts that only contain 4chan.org as a substring."""
    scraper = FourChanScraper()

    spoofed = scraper.parse_url("https://not4chan.org/boards.4chan.org/g/thread/123")
    assert spoofed is None


def test_build_session_base_name_limits_length_and_sanitizes():
    """Ensure session base names are sanitized and length-limited."""
    scraper = FourChanScraper()
    long_board = "a" * (Config.MAX_FOLDER_NAME_LENGTH + 10)
    base = scraper.build_session_base_name(
        {"board": long_board, "type": "board", "thread_id": None}
    )

    assert len(base) <= Config.MAX_FOLDER_NAME_LENGTH
    assert "/" not in base and "\\" not in base
    assert base  # non-empty


def test_download_file_adds_hash_while_mutex_is_held(
    monkeypatch, tmp_path: Path
) -> None:
    """Successful downloads should add hashes while holding the stats mutex."""

    class RecordingMutex:
        def __init__(self) -> None:
            self.depth = 0

        def lock(self) -> None:
            self.depth += 1

        def unlock(self) -> None:
            self.depth -= 1

    class RecordingSet:
        def __init__(self, mutex: RecordingMutex) -> None:
            self.added_while_locked: list[bool] = []
            self.values: set[str] = set()
            self._mutex = mutex

        def add(self, value: str) -> None:
            self.added_while_locked.append(self._mutex.depth > 0)
            self.values.add(value)

        def __contains__(self, value: object) -> bool:
            return value in self.values

    class FakeResponse:
        status_code = 200
        headers = {"content-length": "4"}

        @staticmethod
        def iter_content(chunk_size: int):
            _ = chunk_size
            yield b"data"

    scraper = FourChanScraper()
    scraper.download_dir = tmp_path
    mutex = RecordingMutex()
    hashes = RecordingSet(mutex)
    scraper.stats_mutex = mutex
    scraper.downloaded_hashes = hashes

    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    monkeypatch.setattr(scraper, "check_disk_space", lambda required_mb=0: True)
    monkeypatch.setattr(scraper.session, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(media, "calculate_hash", lambda _path: "hash-123")

    assert scraper.download_file(media, "g-123") is True
    assert hashes.values == {"hash-123"}
    assert hashes.added_while_locked == [True]
