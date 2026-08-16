"""Logic tests for FourChanScraper utilities."""

import base64
import hashlib
from pathlib import Path
from typing import ClassVar

import pytest
import requests

from four_charm import config
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
        headers: ClassVar[dict[str, str]] = {"content-length": "4"}

        @staticmethod
        def iter_content(chunk_size: int):
            _ = chunk_size
            yield b"data"

    class FakeBoardApi:
        def stream_range(self, url, *, headers=None, timeout=None):
            return FakeResponse()

        def fetch_thread(self, board, thread_id):
            raise NotImplementedError

        def fetch_catalog(self, board):
            raise NotImplementedError

    scraper = FourChanScraper(board_api=FakeBoardApi())
    scraper.download_dir = tmp_path

    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    monkeypatch.setattr(scraper, "check_disk_space", lambda required_mb=0: True)
    monkeypatch.setattr(media, "calculate_hash", lambda _path: "hash-123")

    assert scraper.download_file(media, "g-123") is True
    # Hash should now be known to the dedup tracker
    assert scraper.dedup.check_and_register("hash-123") is True


def test_check_existing_file_resumes_partial_when_size_known(tmp_path: Path) -> None:
    """A shorter-than-expected file must not be treated as already complete."""
    scraper = FourChanScraper()
    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    media.size = 100
    path = tmp_path / "123.jpg"
    path.write_bytes(b"partial")

    assert scraper._check_existing_file(path, media) is False
    assert path.exists()
    assert media.skip_reason is None


def test_check_existing_file_skips_complete_size_match(tmp_path: Path) -> None:
    scraper = FourChanScraper()
    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    media.size = 4
    path = tmp_path / "123.jpg"
    path.write_bytes(b"data")

    assert scraper._check_existing_file(path, media) is True
    assert media.skip_reason == "skipped"


def test_check_existing_file_redownloads_oversized(tmp_path: Path) -> None:
    scraper = FourChanScraper()
    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    media.size = 2
    path = tmp_path / "123.jpg"
    path.write_bytes(b"data")

    assert scraper._check_existing_file(path, media) is False
    assert path.exists()
    assert path.read_bytes() == b"data"
    backup = path.with_name(path.name + ".4charm-oversized.bak")
    assert not backup.exists()


def test_download_file_restores_oversized_backup_when_redownload_fails(
    monkeypatch, tmp_path: Path
) -> None:
    """Quarantined oversized files must return if the replacement download fails."""
    scraper = FourChanScraper()
    scraper.download_dir = tmp_path
    dest = tmp_path / "g-123" / "123.jpg"
    dest.parent.mkdir()
    dest.write_bytes(b"data")
    backup = dest.with_name(dest.name + ".4charm-oversized.bak")

    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    media.size = 2

    class FailingBoardApi:
        def stream_range(self, url, *, headers=None, timeout=None):
            _ = url, headers, timeout
            raise ConnectionError("network down")

        def fetch_thread(self, board, thread_id):
            raise NotImplementedError

        def fetch_catalog(self, board):
            raise NotImplementedError

    scraper._board_api = FailingBoardApi()
    monkeypatch.setattr(scraper, "check_disk_space", lambda required_mb=0: True)
    monkeypatch.setattr(config, "MAX_RETRIES", 1)

    assert scraper.download_file(media, "g-123") is False
    assert not backup.exists()
    assert dest.exists()
    assert dest.read_bytes() == b"data"


def test_download_file_resumes_partial_instead_of_skipping(
    monkeypatch, tmp_path: Path
) -> None:
    """Failed leftover bytes should be Range-resumed, not skipped as complete."""
    captured_headers: dict[str, str] = {}

    class FakeResponse:
        status_code = 206
        headers: ClassVar[dict[str, str]] = {"content-length": "2"}

        @staticmethod
        def iter_content(chunk_size: int):
            _ = chunk_size
            yield b"ta"

    class FakeBoardApi:
        def stream_range(self, url, *, headers=None, timeout=None):
            _ = url, timeout
            captured_headers.update(headers or {})
            return FakeResponse()

        def fetch_thread(self, board, thread_id):
            raise NotImplementedError

        def fetch_catalog(self, board):
            raise NotImplementedError

    scraper = FourChanScraper(board_api=FakeBoardApi())
    scraper.download_dir = tmp_path
    dest = tmp_path / "g-123" / "123.jpg"
    dest.parent.mkdir()
    dest.write_bytes(b"da")

    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    media.size = 4
    monkeypatch.setattr(scraper, "check_disk_space", lambda required_mb=0: True)
    monkeypatch.setattr(media, "calculate_hash", lambda _path: "hash-resume")

    assert scraper.download_file(media, "g-123") is True
    assert captured_headers.get("Range") == "bytes=2-"
    assert dest.read_bytes() == b"data"


def test_extract_thread_title_prefers_subject_over_comment() -> None:
    posts = [{"sub": "Subject line", "com": "<p>Comment body</p>"}]
    assert FourChanScraper._extract_thread_title(posts) == "Subject line"


def test_extract_thread_title_strips_html_and_limits_comment() -> None:
    posts = [
        {
            "com": "<blockquote>Line one</blockquote><br>Line   two " + ("x" * 80),
        }
    ]
    title = FourChanScraper._extract_thread_title(posts)
    assert title is not None
    assert "<" not in title
    assert len(title) <= 60
    assert title.startswith("Line one")


def test_extract_thread_title_returns_none_for_empty_posts() -> None:
    assert FourChanScraper._extract_thread_title([]) is None
    assert FourChanScraper._extract_thread_title([{"com": "   "}]) is None
    assert FourChanScraper._extract_thread_title([{"sub": ""}]) is None


def test_extract_thread_title_falls_through_empty_subject_to_comment() -> None:
    posts = [{"sub": "", "com": "<b>Fallback</b> title"}]
    assert FourChanScraper._extract_thread_title(posts) == "Fallback title"


def test_mark_download_cancelled_restores_oversized_backup(tmp_path: Path) -> None:
    """Cancellation after quarantine must put the original bytes back on disk."""
    scraper = FourChanScraper()
    dest = tmp_path / "123.jpg"
    backup = dest.with_name(dest.name + ".4charm-oversized.bak")
    original = b"original oversized bytes"
    backup.write_bytes(original)

    assert scraper._mark_download_cancelled("https://i.4cdn.org/g/123.jpg", dest) is False

    assert dest.exists()
    assert dest.read_bytes() == original
    assert not backup.exists()


def test_download_success_keeps_unrelated_existing_file(monkeypatch, tmp_path: Path) -> None:
    """A different file that already occupies the dest name must not be replaced."""

    class FakeResponse:
        status_code = 200
        headers: ClassVar[dict[str, str]] = {"content-length": "4"}

        @staticmethod
        def iter_content(chunk_size: int):
            _ = chunk_size
            yield b"data"

    class FakeBoardApi:
        def stream_range(self, url, *, headers=None, timeout=None):
            return FakeResponse()

        def fetch_thread(self, board, thread_id):
            raise NotImplementedError

        def fetch_catalog(self, board):
            raise NotImplementedError

    scraper = FourChanScraper(board_api=FakeBoardApi())
    scraper.download_dir = tmp_path

    original = b"too big"
    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    media.size = 4

    dest = tmp_path / "g-123" / "123.jpg"
    dest.parent.mkdir()
    dest.write_bytes(original)

    monkeypatch.setattr(scraper, "check_disk_space", lambda required_mb=0: True)
    monkeypatch.setattr(media, "calculate_hash", lambda _path: "hash-success")

    assert scraper.download_file(media, "g-123") is True
    assert dest.read_bytes() == original
    unique = dest.with_name("123 2.jpg")
    assert unique.read_bytes() == b"data"
    assert not dest.with_name(dest.name + ".4charm-oversized.bak").exists()
    assert not dest.with_name(dest.name + ".4charm.part").exists()


def test_download_disk_space_failure_restores_oversized_backup(
    monkeypatch, tmp_path: Path
) -> None:
    scraper = FourChanScraper()
    scraper.download_dir = tmp_path

    original = b"oversized original"
    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    media.size = 4

    dest = tmp_path / "g-123" / "123.jpg"
    dest.parent.mkdir()
    dest.write_bytes(original)

    monkeypatch.setattr(scraper, "check_disk_space", lambda required_mb=0: False)

    assert scraper.download_file(media, "g-123") is False
    assert dest.exists()
    assert dest.read_bytes() == original
    backup = dest.with_name(dest.name + ".4charm-oversized.bak")
    assert not backup.exists()


def test_check_existing_file_leaves_oversized_file_in_place(tmp_path: Path) -> None:
    """An oversized occupant is left alone so a later download can uniquify."""
    scraper = FourChanScraper()
    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    media.size = 2
    path = tmp_path / "123.jpg"
    path.write_bytes(b"data")

    assert scraper._check_existing_file(path, media) is False
    assert path.exists()
    assert path.read_bytes() == b"data"
    backup = path.with_name(path.name + ".4charm-oversized.bak")
    assert not backup.exists()


def test_download_file_restores_oversized_on_failure(
    monkeypatch, tmp_path: Path
) -> None:
    """If re-download of an oversized file fails, the original bytes are restored."""

    class FailingBoardApi:
        def stream_range(self, url, *, headers=None, timeout=None):
            raise requests.RequestException("network failure")

        def fetch_thread(self, board, thread_id):
            raise NotImplementedError

        def fetch_catalog(self, board):
            raise NotImplementedError

    scraper = FourChanScraper(board_api=FailingBoardApi())
    scraper.download_dir = tmp_path

    original = b"this file is too big"
    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")
    media.size = 4

    dest = tmp_path / "g-123" / "123.jpg"
    dest.parent.mkdir()
    dest.write_bytes(original)

    monkeypatch.setattr(scraper, "check_disk_space", lambda required_mb=0: True)
    monkeypatch.setattr(config, "MAX_RETRIES", 1)
    monkeypatch.setattr(scraper, "calculate_retry_delay", lambda attempt: 0)

    assert scraper.download_file(media, "g-123") is False
    assert dest.exists()
    assert dest.read_bytes() == original
    assert not (dest.parent / (dest.name + ".4charm-oversized.bak")).exists()

def test_check_existing_file_marks_session_duplicate(tmp_path: Path) -> None:
    """A file whose hash was already downloaded this session is a duplicate."""
    scraper = FourChanScraper()
    scraper.download_dir = tmp_path
    file_path = tmp_path / "existing.jpg"
    file_path.write_bytes(b"duplicate-content")
    media = MediaFile("https://i.4cdn.org/g/1.jpg", "existing.jpg")

    scraper.dedup.add("dup-hash")
    media.calculate_hash = lambda _path: "dup-hash"  # ty: ignore[invalid-assignment]

    assert scraper._check_existing_file(file_path, media) is True
    assert media.skip_reason == "duplicate"
    assert scraper.stats["duplicates"] == 1


def test_check_existing_file_skips_unchanged_on_disk(tmp_path: Path) -> None:
    """An on-disk file with a new hash is skipped without re-downloading."""
    scraper = FourChanScraper()
    scraper.download_dir = tmp_path
    file_path = tmp_path / "on-disk.jpg"
    file_path.write_bytes(b"already-here")
    media = MediaFile("https://i.4cdn.org/g/2.jpg", "on-disk.jpg")

    media.calculate_hash = lambda _path: "fresh-hash"  # ty: ignore[invalid-assignment]

    assert scraper._check_existing_file(file_path, media) is True
    assert media.skip_reason == "skipped"
    assert media.downloaded is True
    assert scraper.stats["skipped"] == 1


def test_extract_media_from_posts_builds_media_files() -> None:
    scraper = FourChanScraper()
    posts = [
        {
            "tim": 123,
            "ext": ".webm",
            "filename": "vid",
            "fsize": 5000,
            "md5": "abc123",
        },
        {"tim": 456, "ext": ".exe", "filename": "bad"},
    ]

    media_files = scraper.extract_media_from_posts(posts, "g", "99")

    assert len(media_files) == 1
    media = media_files[0]
    assert media.url == "https://i.4cdn.org/g/123.webm"
    assert media.filename.endswith(".webm")
    assert media.board == "g"
    assert media.thread_id == "99"
    assert media.size == 5000
    assert media.expected_md5 == "abc123"


def test_download_file_retries_after_verification_failure(
    monkeypatch, tmp_path: Path
) -> None:
    """Corrupt first attempt is deleted and a verified retry succeeds."""
    good_content = b"verified-download-bytes"
    md5_digest = hashlib.md5(good_content).digest()
    expected_md5 = base64.b64encode(md5_digest).decode("ascii")

    class BadResponse:
        status_code = 200
        headers: ClassVar[dict[str, str]] = {"content-length": str(len(good_content))}

        @staticmethod
        def iter_content(chunk_size: int):
            _ = chunk_size
            yield b"corrupt"

    class GoodResponse:
        status_code = 200
        headers: ClassVar[dict[str, str]] = {"content-length": str(len(good_content))}

        @staticmethod
        def iter_content(chunk_size: int):
            _ = chunk_size
            yield good_content

    class FlipBoardApi:
        def __init__(self) -> None:
            self.attempt = 0

        def stream_range(self, url, *, headers=None, timeout=None):
            self.attempt += 1
            if self.attempt == 1:
                return BadResponse()
            return GoodResponse()

        def fetch_thread(self, board, thread_id):
            raise NotImplementedError

        def fetch_catalog(self, board):
            raise NotImplementedError

    api = FlipBoardApi()
    scraper = FourChanScraper(board_api=api)
    scraper.download_dir = tmp_path
    monkeypatch.setattr(scraper, "check_disk_space", lambda required_mb=0: True)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    media = MediaFile("https://i.4cdn.org/g/retry.jpg", "retry.jpg")
    media.size = len(good_content)
    media.expected_md5 = expected_md5

    assert scraper.download_file(media, "g-retry") is True
    assert api.attempt == 2
    assert scraper.stats["downloaded"] == 1
