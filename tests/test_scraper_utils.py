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


def test_download_file_registers_hash_in_dedup_tracker(
    monkeypatch, tmp_path: Path
) -> None:
    """Successful downloads should register the file hash in the DedupTracker."""

    class FakeResponse:
        status_code = 200
        headers = {"content-length": "4"}

        @staticmethod
        def iter_content(chunk_size: int):
            _ = chunk_size
            yield b"data"

    scraper = FourChanScraper()
    scraper.download_dir = tmp_path

    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    monkeypatch.setattr(scraper, "check_disk_space", lambda required_mb=0: True)
    monkeypatch.setattr(scraper.session, "get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(media, "calculate_hash", lambda _path: "hash-123")

    assert scraper.download_file(media, "g-123") is True
    # Hash should now be known to the dedup tracker
    assert scraper.dedup.check_and_register("hash-123") is True
