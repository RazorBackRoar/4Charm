"""Tests for thread-safe SHA-256 deduplication."""

import threading

from four_charm.core.dedup import DedupTracker


def test_check_and_register_marks_first_hash_as_new() -> None:
    tracker = DedupTracker()

    assert tracker.check_and_register("hash-a") is False
    assert tracker.check_and_register("hash-a") is True


def test_add_registers_without_duplicate_signal() -> None:
    tracker = DedupTracker()

    tracker.add("hash-b")
    assert tracker.check_and_register("hash-b") is True


def test_check_and_register_is_thread_safe() -> None:
    tracker = DedupTracker()
    seen_duplicates: list[bool] = []

    def worker() -> None:
        for index in range(50):
            is_duplicate = tracker.check_and_register(f"hash-{index % 10}")
            if is_duplicate:
                seen_duplicates.append(True)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert seen_duplicates
