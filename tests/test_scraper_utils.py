"""Logic tests for FourChanScraper utilities."""

from pathlib import Path

import pytest

import four_charm.config as config
from four_charm.core.models import MediaFile
from four_charm.core.scraper import FourChanScraper, _rc_sanitize_filename


def test_parse_url_thread_and_catalog():
    """Parse thread, catalog, and invalid URLs."""
    scraper = FourChanScraper()

    thread = scraper.parse_url("https://boards.4chan.org/g/thread/123456789")
    catalog = scraper.parse_url("https://boards.4chan.org/g/catalog")
    channel_thread = scraper.parse_url("https://boards.4channel.org/g/thread/42")
    media = scraper.parse_url("https://i.4cdn.org/g/1234567890.webm")
    invalid = scraper.parse_url("https://example.com/not-4chan")

    assert thread == {"board": "g", "type": "thread", "thread_id": "123456789"}
    assert catalog == {"board": "g", "type": "catalog", "thread_id": None}
    assert channel_thread == {"board": "g", "type": "thread", "thread_id": "42"}
    assert media == {
        "board": "g",
        "type": "media",
        "thread_id": None,
        "media_filename": "1234567890.webm",
        "media_url": "https://i.4cdn.org/g/1234567890.webm",
    }
    assert invalid is None


def test_parse_url_rejects_hostname_substring_spoof():
    """Reject hosts that only contain 4chan.org as a substring."""
    scraper = FourChanScraper()

    spoofed = scraper.parse_url("https://not4chan.org/boards.4chan.org/g/thread/123")
    assert spoofed is None


def test_rc_sanitize_filename_respects_max_length_and_extension():
    """4Charm download paths must stay within MAX_FILENAME_LENGTH after razorcore migration."""
    long_name = "x" * (config.MAX_FILENAME_LENGTH + 50) + ".jpg"
    sanitized = _rc_sanitize_filename(long_name)

    assert len(sanitized) <= config.MAX_FILENAME_LENGTH
    assert sanitized.endswith(".jpg")
    assert sanitized != "unnamed_file"


def test_build_session_base_name_limits_length_and_sanitizes():
    """Ensure session base names are sanitized and length-limited."""
    scraper = FourChanScraper()
    long_board = "a" * (config.MAX_FOLDER_NAME_LENGTH + 10)
    base = scraper.build_session_base_name(
        {"board": long_board, "type": "board", "thread_id": None}
    )

    assert len(base) <= config.MAX_FOLDER_NAME_LENGTH
    assert "/" not in base and "\\" not in base
    assert base  # non-empty


def test_assert_within_download_dir_blocks_escape(tmp_path: Path) -> None:
    """Resolved paths outside the download root must be rejected."""
    scraper = FourChanScraper()
    scraper.download_dir = tmp_path / "downloads"
    scraper.download_dir.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.touch()

    with pytest.raises(ValueError, match="outside download directory"):
        scraper._assert_within_download_dir(outside)


def test_prepare_download_path_sanitizes_parent_segments(tmp_path: Path) -> None:
    """Folder names with parent segments are flattened before writing."""
    scraper = FourChanScraper()
    scraper.download_dir = tmp_path / "downloads"
    scraper.download_dir.mkdir(parents=True)

    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    file_path, save_dir = scraper._prepare_download_path(media, "../outside")

    assert file_path.is_relative_to(scraper.download_dir)
    assert ".." not in str(save_dir)


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
    monkeypatch.setattr(
        "four_charm.core.scraper.safe_get",
        lambda _session, _url, **_kwargs: FakeResponse(),
    )
    monkeypatch.setattr(media, "calculate_hash", lambda _path: "hash-123")

    assert scraper.download_file(media, "g-123") is True
    # Hash should now be known to the dedup tracker
    assert scraper.dedup.check_and_register("hash-123") is True
