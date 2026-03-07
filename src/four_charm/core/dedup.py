"""Thread-safe SHA-256 deduplication state for downloaded files.

Encapsulates the seen-hash set and its lock so that concurrency
safety is explicit and testable in isolation. No Qt dependencies.
"""

from __future__ import annotations

import threading


class DedupTracker:
    """Thread-safe set of seen file hashes."""

    def __init__(self) -> None:
        self._hashes: set[str] = set()
        self._lock = threading.Lock()

    def check_and_register(self, file_hash: str) -> bool:
        """Atomically check if *file_hash* is known and register it.

        Returns True if the hash was already present (duplicate).
        """
        with self._lock:
            if file_hash in self._hashes:
                return True
            self._hashes.add(file_hash)
            return False

    def add(self, file_hash: str) -> None:
        """Register a hash as seen. Thread-safe."""
        with self._lock:
            self._hashes.add(file_hash)
