"""Tests for bandwidth monitoring functionality."""

import time

import pytest

from four_charm.core.bandwidth import BandwidthMonitor


def test_bandwidth_monitor_initialization():
    """Test BandwidthMonitor initializes with correct defaults."""
    monitor = BandwidthMonitor()
    assert monitor.window_seconds == 5.0
    assert monitor.peak_speed == 0.0
    assert monitor.total_bytes == 0
    assert len(monitor.samples) == 0


def test_bandwidth_monitor_custom_window():
    """Test BandwidthMonitor accepts custom window size."""
    monitor = BandwidthMonitor(window_seconds=10.0)
    assert monitor.window_seconds == 10.0


def test_record_progress():
    """Test recording download progress."""
    monitor = BandwidthMonitor()
    monitor.record_progress(1024)
    assert monitor.total_bytes == 1024
    assert len(monitor.samples) == 1


def test_get_current_speed_insufficient_data():
    """Test speed calculation returns 0 with insufficient data."""
    monitor = BandwidthMonitor()
    assert monitor.get_current_speed() == 0.0

    monitor.record_progress(1024)
    assert monitor.get_current_speed() == 0.0  # Need at least 2 samples


def test_get_current_speed_calculation(monkeypatch):
    """Test speed calculation with mocked time."""
    monitor = BandwidthMonitor()

    # Mock time to control timestamps
    times = [100.0, 101.0]  # 1 second apart
    time_iter = iter(times)
    monkeypatch.setattr(time, "time", lambda: next(time_iter))

    monitor.record_progress(1024 * 1024)  # 1 MB at t=100
    monitor.record_progress(1024 * 1024)  # 1 MB at t=101

    speed = monitor.get_current_speed()
    assert speed == pytest.approx(2.0, rel=0.01)  # 2 MB in 1 second = 2 MB/s


def test_rolling_window_removes_old_samples(monkeypatch):
    """Test that old samples outside the window are removed."""
    monitor = BandwidthMonitor(window_seconds=2.0)

    times = [100.0, 101.0, 103.0]  # Last sample is 3 seconds after first
    time_iter = iter(times)
    monkeypatch.setattr(time, "time", lambda: next(time_iter))

    monitor.record_progress(1024)  # t=100
    monitor.record_progress(1024)  # t=101
    assert len(monitor.samples) == 2

    monitor.record_progress(1024)  # t=103, should remove both old samples (>2s old)
    assert len(monitor.samples) == 1  # Only t=103 sample remains


def test_peak_speed_tracking(monkeypatch):
    """Test that peak speed is tracked correctly."""
    monitor = BandwidthMonitor()

    times = [100.0, 101.0, 102.0, 103.0]
    time_iter = iter(times)
    monkeypatch.setattr(time, "time", lambda: next(time_iter))

    monitor.record_progress(1024 * 1024)  # 1 MB
    monitor.record_progress(1024 * 1024)  # 1 MB
    speed1 = monitor.get_current_speed()

    monitor.record_progress(2 * 1024 * 1024)  # 2 MB
    speed2 = monitor.get_current_speed()

    assert monitor.peak_speed >= max(speed1, speed2)


def test_calculate_eta_zero_speed():
    """Test ETA calculation returns 0 when speed is zero."""
    monitor = BandwidthMonitor()
    eta = monitor.calculate_eta(1024 * 1024)
    assert eta == 0.0


def test_calculate_eta_with_speed(monkeypatch):
    """Test ETA calculation with known speed."""
    monitor = BandwidthMonitor()

    times = [100.0, 101.0]
    time_iter = iter(times)
    monkeypatch.setattr(time, "time", lambda: next(time_iter))

    monitor.record_progress(1024 * 1024)  # 1 MB
    monitor.record_progress(1024 * 1024)  # 1 MB

    # Speed is 2 MB/s, remaining is 10 MB
    eta = monitor.calculate_eta(10 * 1024 * 1024)
    assert eta == pytest.approx(5.0, rel=0.01)  # 10 MB / 2 MB/s = 5 seconds


def test_format_speed_kb():
    """Test speed formatting for values < 0.1 MB/s."""
    monitor = BandwidthMonitor()
    assert monitor.format_speed(0.05) == "51.2 KB/s"


def test_format_speed_mb():
    """Test speed formatting for values >= 0.1 MB/s."""
    monitor = BandwidthMonitor()
    assert monitor.format_speed(1.5) == "1.5 MB/s"
    assert monitor.format_speed(10.0) == "10.0 MB/s"


def test_format_eta_seconds():
    """Test ETA formatting for values < 60 seconds."""
    monitor = BandwidthMonitor()
    assert monitor.format_eta(30) == "30s"
    assert monitor.format_eta(59) == "59s"


def test_format_eta_minutes():
    """Test ETA formatting for values < 3600 seconds."""
    monitor = BandwidthMonitor()
    assert monitor.format_eta(90) == "1m 30s"
    assert monitor.format_eta(3599) == "59m 59s"


def test_format_eta_hours():
    """Test ETA formatting for values >= 3600 seconds."""
    monitor = BandwidthMonitor()
    assert monitor.format_eta(3600) == "1h 0m"
    assert monitor.format_eta(3661) == "1h 1m"
    assert monitor.format_eta(7200) == "2h 0m"


def test_reset():
    """Test reset clears all tracking data."""
    monitor = BandwidthMonitor()
    monitor.record_progress(1024)
    monitor.record_progress(2048)
    monitor.peak_speed = 5.0

    monitor.reset()

    assert len(monitor.samples) == 0
    assert monitor.peak_speed == 0.0
    assert monitor.total_bytes == 0
