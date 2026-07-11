"""Regression: cancel must not permanently disable later download runs."""

from __future__ import annotations

from four_charm.core.scraper import FourChanScraper


def test_prepare_for_download_clears_sticky_cancel_flag() -> None:
    """Cancel leaves cancelled=True; the next session must clear it.

    Concrete trigger: user clicks Cancel mid-run, then Start Download again.
    Without a reset, every download_file call fails immediately via
    _ensure_active_download because the shared scraper keeps cancelled=True.
    """
    scraper = FourChanScraper()
    scraper.cancel_downloads()
    assert scraper.cancelled is True

    scraper.prepare_for_download()

    assert scraper.cancelled is False
    assert scraper.paused is False
    assert scraper._ensure_active_download("https://example.com/a.jpg") is True


def test_prepare_for_download_resets_per_run_stats() -> None:
    scraper = FourChanScraper()
    scraper.stats["downloaded"] = 7
    scraper.stats["failed"] = 2
    scraper.stats["duplicates"] = 3
    scraper.stats["size_mb"] = 12.5

    scraper.prepare_for_download()

    assert scraper.stats["downloaded"] == 0
    assert scraper.stats["failed"] == 0
    assert scraper.stats["duplicates"] == 0
    assert scraper.stats["size_mb"] == 0.0
    assert scraper.stats["total"] == 0
