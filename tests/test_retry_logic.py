"""Tests for exponential backoff retry logic."""

import four_charm.config as config
from four_charm.core.scraper import FourChanScraper


def test_calculate_retry_delay_exponential_growth():
    """Test that retry delay grows exponentially."""
    scraper = FourChanScraper()

    delay0 = scraper.calculate_retry_delay(0)
    delay1 = scraper.calculate_retry_delay(1)
    delay2 = scraper.calculate_retry_delay(2)
    delay3 = scraper.calculate_retry_delay(3)

    # Remove jitter for comparison (subtract 1 second max jitter)
    assert delay0 >= 1.0 and delay0 <= 2.0  # 2^0 * 1.0 + jitter = 1.0-2.0
    assert delay1 >= 2.0 and delay1 <= 3.0  # 2^1 * 1.0 + jitter = 2.0-3.0
    assert delay2 >= 4.0 and delay2 <= 5.0  # 2^2 * 1.0 + jitter = 4.0-5.0
    assert delay3 >= 8.0 and delay3 <= 9.0  # 2^3 * 1.0 + jitter = 8.0-9.0


def test_calculate_retry_delay_with_custom_base():
    """Test retry delay with custom base delay."""
    scraper = FourChanScraper()

    delay = scraper.calculate_retry_delay(0, base_delay=2.0)
    assert delay >= 2.0 and delay <= 3.0  # 2^0 * 2.0 + jitter = 2.0-3.0


def test_calculate_retry_delay_max_cap():
    """Test that retry delay is capped at MAX_RETRY_DELAY."""
    scraper = FourChanScraper()

    # Attempt 10 should exceed 60 seconds without cap (2^10 = 1024)
    delay = scraper.calculate_retry_delay(10)
    assert delay <= config.MAX_RETRY_DELAY + 1.0  # Cap + max jitter


def test_calculate_retry_delay_has_jitter():
    """Test that jitter is applied (delays vary)."""
    scraper = FourChanScraper()

    delays = [scraper.calculate_retry_delay(2) for _ in range(10)]

    # All delays should be in expected range
    for delay in delays:
        assert delay >= 4.0 and delay <= 5.0

    # Delays should vary (not all identical) due to jitter
    assert len(set(delays)) > 1


def test_calculate_retry_delay_uses_config_default():
    """Test that default base delay comes from config."""
    scraper = FourChanScraper()

    delay = scraper.calculate_retry_delay(0)
    expected_min = config.BASE_RETRY_DELAY
    expected_max = config.BASE_RETRY_DELAY + 1.0

    assert delay >= expected_min and delay <= expected_max


def test_select_chunk_size_small_file():
    """Test chunk size selection for small files (<10MB)."""
    scraper = FourChanScraper()

    chunk_size = scraper.select_chunk_size(5 * 1024 * 1024)  # 5 MB
    assert chunk_size == 8192  # 8 KB


def test_select_chunk_size_medium_file():
    """Test chunk size selection for medium files (10-100MB)."""
    scraper = FourChanScraper()

    chunk_size = scraper.select_chunk_size(50 * 1024 * 1024)  # 50 MB
    assert chunk_size == 65536  # 64 KB


def test_select_chunk_size_large_file():
    """Test chunk size selection for large files (>=100MB)."""
    scraper = FourChanScraper()

    chunk_size = scraper.select_chunk_size(200 * 1024 * 1024)  # 200 MB
    assert chunk_size == 262144  # 256 KB


def test_select_chunk_size_boundary_10mb():
    """Test chunk size at 10MB boundary."""
    scraper = FourChanScraper()

    # Just under 10MB
    chunk_size = scraper.select_chunk_size(10 * 1024 * 1024 - 1)
    assert chunk_size == 8192

    # Exactly 10MB
    chunk_size = scraper.select_chunk_size(10 * 1024 * 1024)
    assert chunk_size == 65536


def test_select_chunk_size_boundary_100mb():
    """Test chunk size at 100MB boundary."""
    scraper = FourChanScraper()

    # Just under 100MB
    chunk_size = scraper.select_chunk_size(100 * 1024 * 1024 - 1)
    assert chunk_size == 65536

    # Exactly 100MB
    chunk_size = scraper.select_chunk_size(100 * 1024 * 1024)
    assert chunk_size == 262144
