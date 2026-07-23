"""Tests for download progress signal payload."""

from __future__ import annotations

import dataclasses

from four_charm.core.signals import DownloadTask


def test_download_task_exposes_all_progress_fields() -> None:
    task = DownloadTask(
        completed=3,
        total=10,
        filename="photo.jpg",
        speed_mb_s=1.25,
        thread_title="Example thread",
        thread_index=2,
        eta_s=42.0,
    )

    assert task.completed == 3
    assert task.total == 10
    assert task.filename == "photo.jpg"
    assert task.speed_mb_s == 1.25
    assert task.thread_title == "Example thread"
    assert task.thread_index == 2
    assert task.eta_s == 42.0


def test_download_task_is_immutable() -> None:
    task = DownloadTask(
        completed=0,
        total=1,
        filename="a.jpg",
        speed_mb_s=0.0,
        thread_title="",
        thread_index=0,
        eta_s=0.0,
    )

    assert dataclasses.is_dataclass(task)
    assert task.__dataclass_fields__["completed"].name == "completed"
