"""Bandwidth monitoring for download progress tracking.

Tracks download speed and calculates ETA using a rolling window approach.
"""

from __future__ import annotations

import time


class BandwidthMonitor:
    """Track bandwidth usage and calculate ETA."""

    def __init__(self, window_seconds: float = 5.0):
        """Initialize bandwidth monitor.

        Args:
            window_seconds: Rolling window size for speed calculation (default 5.0)
        """
        self.samples: list[tuple[float, int]] = []  # (timestamp, bytes)
        self.window_seconds = window_seconds
        self.peak_speed = 0.0
        self.total_bytes = 0

    def record_progress(self, bytes_downloaded: int) -> None:
        """Record download progress.

        Args:
            bytes_downloaded: Number of bytes downloaded in this update
        """
        now = time.time()
        self.samples.append((now, bytes_downloaded))
        self.total_bytes += bytes_downloaded

        # Remove old samples outside window
        cutoff = now - self.window_seconds
        self.samples = [(t, b) for t, b in self.samples if t > cutoff]

    def get_current_speed(self) -> float:
        """Get current download speed in MB/s.

        Returns:
            Current speed in MB/s (0.0 if insufficient data)
        """
        if len(self.samples) < 2:
            return 0.0

        time_span = self.samples[-1][0] - self.samples[0][0]
        if time_span == 0:
            return 0.0

        total_bytes = sum(b for _, b in self.samples)
        speed_mbps = (total_bytes / time_span) / (1024 * 1024)

        self.peak_speed = max(self.peak_speed, speed_mbps)
        return speed_mbps

    def calculate_eta(self, bytes_remaining: int) -> float:
        """Calculate estimated time remaining in seconds.

        Args:
            bytes_remaining: Number of bytes left to download

        Returns:
            Estimated seconds remaining (0.0 if speed is zero)
        """
        speed = self.get_current_speed()
        if speed == 0:
            return 0.0

        speed_bytes = speed * 1024 * 1024
        return bytes_remaining / speed_bytes

    def format_speed(self, speed_mbps: float) -> str:
        """Format speed for display.

        Args:
            speed_mbps: Speed in MB/s

        Returns:
            Formatted speed string (e.g., "1.5 MB/s" or "512.0 KB/s")
        """
        if speed_mbps < 0.1:
            return f"{speed_mbps * 1024:.1f} KB/s"
        else:
            return f"{speed_mbps:.1f} MB/s"

    def format_eta(self, seconds: float) -> str:
        """Format ETA for display.

        Args:
            seconds: Estimated seconds remaining

        Returns:
            Formatted ETA string (e.g., "5m 30s" or "1h 15m")
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def reset(self) -> None:
        """Reset all tracking data."""
        self.samples.clear()
        self.peak_speed = 0.0
        self.total_bytes = 0
