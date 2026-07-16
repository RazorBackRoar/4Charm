"""Adaptive chunk-size selection for streaming downloads.

Picks one of three chunk sizes based on the file's total size. Threshold
values and chunk sizes come from ``four_charm.config`` so user preferences
flow through automatically.
"""

from __future__ import annotations

import four_charm.config as config


class ChunkSelector:
    """Pick a streaming chunk size from configured size buckets."""

    def __init__(
        self,
        thresholds: tuple[int, int] | None = None,
        sizes: tuple[int, int, int] | None = None,
    ) -> None:
        configured_thresholds = (
            thresholds
            if thresholds is not None
            else config.ADAPTIVE_CHUNK_THRESHOLDS
        )
        configured_sizes = sizes if sizes is not None else config.CHUNK_SIZES
        self.threshold_small, self.threshold_large = configured_thresholds
        self.size_small, self.size_medium, self.size_large = configured_sizes

    def select_chunk_size(self, file_size: int) -> int:
        """Return a chunk size in bytes for a file of ``file_size`` bytes.

        Files under ``threshold_small`` (default 10MB) get the smallest chunk
        (8KB) for fast feedback; mid-sized files (10MB-100MB) get 64KB; large
        files (100MB+) get 256KB for throughput.
        """
        if file_size < self.threshold_small:
            return self.size_small
        if file_size < self.threshold_large:
            return self.size_medium
        return self.size_large
