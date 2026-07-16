"""Progress signal payload for download workers.

``DownloadTask`` is the structured value carried by the workers' ``progress``
signal. The schema preserves the seven fields the GUI needs (count, total,
filename, speed, thread title, thread index, ETA) but exposes them as
typed attributes instead of a positional tuple. Tuple-ordering knowledge
moves from four call sites into one factory.

The signal is still emitted as a single object — ``Signal(object)`` — so the
PySide6 thread-boundary contract is preserved.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadTask:
    """One progress update for the GUI.

    Attributes:
        completed: Number of files completed so far in this run.
        total: Total files scheduled for this run.
        filename: Name of the most recently completed file.
        speed_mb_s: Rolling average download speed in MB/s.
        thread_title: Display title for the thread, or empty for single-URL
            flows.
        thread_index: 1-based index of the thread within a multi-URL run, or
            0 for single-URL flows.
        eta_s: Estimated seconds remaining for the whole run (0.0 if unknown).
    """

    completed: int
    total: int
    filename: str
    speed_mb_s: float
    thread_title: str
    thread_index: int
    eta_s: float
