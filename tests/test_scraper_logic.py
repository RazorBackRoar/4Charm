"""Logic tests for FourChanScraper."""

import pytest
from four_charm.core.scraper import FourChanScraper
from four_charm.config import Config


def test_sanitize_filename():
    """Test filename sanitization."""
    scraper = FourChanScraper()

    # Normal filename
    assert scraper.sanitize_filename("test.jpg") == "test.jpg"

    # Reserved names
    assert scraper.sanitize_filename("CON.jpg") == "_CON.jpg"
    assert scraper.sanitize_filename("aux.png") == "_aux.png"

    # Invalid characters
    assert scraper.sanitize_filename("test/file.jpg") == "test_file.jpg"
    assert scraper.sanitize_filename("test:file.jpg") == "test_file.jpg"
    assert scraper.sanitize_filename('test"file.jpg') == "test_file.jpg"

    # Truncation (assuming MAX_FILENAME_LENGTH is e.g. 200)
    long_name = "a" * (Config.MAX_FILENAME_LENGTH + 10) + ".jpg"
    sanitized = scraper.sanitize_filename(long_name)
    assert len(sanitized) <= Config.MAX_FILENAME_LENGTH
    assert sanitized.endswith(".jpg")


def test_extract_media_from_posts():
    """Test media extraction from post data."""
    scraper = FourChanScraper()
    board = "g"
    thread_id = "123456"

    posts = [
        {
            # Valid image
            "tim": 1234567890,
            "ext": ".jpg",
            "filename": "my_image",
            "fsize": 1024,
        },
        {
            # Valid video
            "tim": 1234567891,
            "ext": ".webm",
            "filename": "my_video",
            "fsize": 2048,
        },
        {
            # Missing tim/ext
            "no": 123,
            "com": "just a comment",
        },
        {
            # Unsupported extension (e.g., .exe if not in allowed list)
            "tim": 1234567892,
            "ext": ".exe",
            "filename": "virus",
        },
    ]

    media_files = scraper.extract_media_from_posts(posts, board, thread_id)

    # Check we got 2 valid files
    assert len(media_files) == 2

    # Check details of first file
    f1 = media_files[0]
    assert f1.board == board
    assert f1.thread_id == thread_id
    assert f1.filename == "my_image.jpg"
    assert f1.url == "https://i.4cdn.org/g/1234567890.jpg"
    assert f1.size == 1024

    # Check details of second file
    f2 = media_files[1]
    assert f2.filename == "my_video.webm"
    assert f2.url == "https://i.4cdn.org/g/1234567891.webm"


def test_sanitize_folder_component():
    """Test folder name sanitization."""
    scraper = FourChanScraper()

    # Basic
    assert scraper._sanitize_folder_component("Cool Thread") == "Cool Thread"

    # Invalid chars
    assert scraper._sanitize_folder_component("Thread/With/Slashes") == "Thread_With_Slashes"

    # Empty
    assert scraper._sanitize_folder_component("") == ""
    assert scraper._sanitize_folder_component(None) == ""
