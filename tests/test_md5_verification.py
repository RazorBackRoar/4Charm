"""Tests for MD5 verification functionality."""

import base64
import hashlib
from pathlib import Path

import pytest

from four_charm.core.models import MediaFile
from four_charm.core.scraper import FourChanScraper


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file with known content."""
    file_path = tmp_path / "test_file.jpg"
    content = b"test content for md5 verification"
    file_path.write_bytes(content)
    return file_path, content


def test_verify_download_file_missing():
    """Test verification fails when file doesn't exist."""
    scraper = FourChanScraper()
    media_file = MediaFile("http://example.com/test.jpg", "test.jpg")

    result = scraper.verify_download(Path("/nonexistent/file.jpg"), media_file)
    assert result is False
    assert media_file.verified is False


def test_verify_download_empty_file(tmp_path):
    """Test verification fails for empty files."""
    scraper = FourChanScraper()
    media_file = MediaFile("http://example.com/test.jpg", "test.jpg")

    empty_file = tmp_path / "empty.jpg"
    empty_file.write_bytes(b"")

    result = scraper.verify_download(empty_file, media_file)
    assert result is False
    assert media_file.verified is False


def test_verify_download_size_mismatch(temp_file):
    """Test verification fails when file size doesn't match."""
    scraper = FourChanScraper()
    file_path, content = temp_file

    media_file = MediaFile("http://example.com/test.jpg", "test.jpg")
    media_file.size = 999  # Wrong size

    result = scraper.verify_download(file_path, media_file)
    assert result is False
    assert media_file.verified is False


def test_verify_download_size_match(temp_file):
    """Test verification passes when file size matches and no MD5."""
    scraper = FourChanScraper()
    file_path, content = temp_file

    media_file = MediaFile("http://example.com/test.jpg", "test.jpg")
    media_file.size = len(content)

    result = scraper.verify_download(file_path, media_file)
    assert result is True
    assert media_file.verified is True


def test_verify_download_md5_match(temp_file):
    """Test verification passes when MD5 matches."""
    scraper = FourChanScraper()
    file_path, content = temp_file

    # Calculate expected MD5
    md5_hash = hashlib.md5(content).digest()
    expected_md5_base64 = base64.b64encode(md5_hash).decode('ascii')

    media_file = MediaFile("http://example.com/test.jpg", "test.jpg")
    media_file.size = len(content)
    media_file.expected_md5 = expected_md5_base64

    result = scraper.verify_download(file_path, media_file)
    assert result is True
    assert media_file.verified is True


def test_verify_download_md5_mismatch(temp_file):
    """Test verification fails when MD5 doesn't match."""
    scraper = FourChanScraper()
    file_path, content = temp_file

    # Use wrong MD5
    wrong_md5 = base64.b64encode(b"wrong_hash_value").decode('ascii')

    media_file = MediaFile("http://example.com/test.jpg", "test.jpg")
    media_file.size = len(content)
    media_file.expected_md5 = wrong_md5

    result = scraper.verify_download(file_path, media_file)
    assert result is False
    assert media_file.verified is False


def test_verify_download_md5_hex_format(temp_file):
    """Test verification works with hex MD5 (fallback for non-base64)."""
    scraper = FourChanScraper()
    file_path, content = temp_file

    # Calculate expected MD5 in base64 format (4chan API format)
    md5_hash = hashlib.md5(content).digest()
    expected_md5_base64 = base64.b64encode(md5_hash).decode('ascii')

    media_file = MediaFile("http://example.com/test.jpg", "test.jpg")
    media_file.size = len(content)
    media_file.expected_md5 = expected_md5_base64

    result = scraper.verify_download(file_path, media_file)
    assert result is True
    assert media_file.verified is True


def test_verify_download_no_size_no_md5(temp_file):
    """Test verification passes when no size or MD5 is provided."""
    scraper = FourChanScraper()
    file_path, _ = temp_file

    media_file = MediaFile("http://example.com/test.jpg", "test.jpg")
    # No size or MD5 set

    result = scraper.verify_download(file_path, media_file)
    assert result is True
    assert media_file.verified is True


def test_media_file_has_verification_fields():
    """Test that MediaFile has expected_md5 and verified fields."""
    media_file = MediaFile("http://example.com/test.jpg", "test.jpg")

    assert hasattr(media_file, 'expected_md5')
    assert hasattr(media_file, 'verified')
    assert media_file.expected_md5 is None
    assert media_file.verified is False


def test_format_error_message_connection_error():
    """Test error message formatting for connection errors."""
    import requests

    scraper = FourChanScraper()
    error = requests.exceptions.ConnectionError("Connection refused")
    context = {'filename': 'test.jpg', 'url': 'http://example.com/test.jpg'}

    message = scraper.format_error_message(error, context)
    assert "Connection failed" in message
    assert "test.jpg" in message
    assert "internet connection" in message


def test_format_error_message_timeout():
    """Test error message formatting for timeout errors."""
    import requests

    scraper = FourChanScraper()
    error = requests.exceptions.Timeout("Request timed out")
    context = {'filename': 'test.jpg', 'timeout': 30}

    message = scraper.format_error_message(error, context)
    assert "timed out" in message
    assert "30s" in message
    assert "test.jpg" in message


def test_format_error_message_http_404():
    """Test error message formatting for 404 errors."""
    import requests

    scraper = FourChanScraper()

    # Create a mock response
    class MockResponse:
        status_code = 404

    error = requests.exceptions.HTTPError("404 Not Found")
    error.response = MockResponse()
    context = {'filename': 'test.jpg'}

    message = scraper.format_error_message(error, context)
    assert "File not found" in message
    assert "test.jpg" in message
    assert "archived or deleted" in message


def test_format_error_message_http_403():
    """Test error message formatting for 403 errors."""
    import requests

    scraper = FourChanScraper()

    class MockResponse:
        status_code = 403

    error = requests.exceptions.HTTPError("403 Forbidden")
    error.response = MockResponse()
    context = {'filename': 'test.jpg'}

    message = scraper.format_error_message(error, context)
    assert "Access denied" in message
    assert "test.jpg" in message


def test_format_error_message_disk_space():
    """Test error message formatting for disk space errors."""
    scraper = FourChanScraper()
    error = OSError("No space left on device")
    context = {'filename': 'test.jpg', 'required_mb': 100, 'available_mb': 50}

    message = scraper.format_error_message(error, context)
    assert "Insufficient disk space" in message
    assert "100MB" in message
    assert "50MB" in message
