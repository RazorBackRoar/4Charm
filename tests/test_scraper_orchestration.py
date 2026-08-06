"""Tests for scrape_thread and scrape_catalog orchestration."""

from unittest.mock import Mock

from four_charm.core.models import MediaFile
from four_charm.core.scraper import FourChanScraper


def test_scrape_thread_extracts_media_and_title(monkeypatch) -> None:
    scraper = FourChanScraper()
    monkeypatch.setattr(
        scraper,
        "get_thread_data",
        lambda board, thread_id: {
            "posts": [
                {
                    "tim": 123,
                    "ext": ".jpg",
                    "filename": "photo",
                    "fsize": 2048,
                    "md5": "abc",
                }
            ],
            "_thread_title": "Catalog thread",
        },
    )

    media_files, title = scraper.scrape_thread("g", "999")

    assert title == "Catalog thread"
    assert len(media_files) == 1
    media = media_files[0]
    assert media.url == "https://i.4cdn.org/g/123.jpg"
    assert media.thread_id == "999"
    assert media.size == 2048
    assert media.expected_md5 == "abc"


def test_scrape_thread_returns_empty_when_api_fails(monkeypatch) -> None:
    scraper = FourChanScraper()
    monkeypatch.setattr(scraper, "get_thread_data", lambda board, thread_id: None)

    media_files, title = scraper.scrape_thread("g", "123")

    assert media_files == []
    assert title is None


def test_scrape_catalog_respects_max_threads(monkeypatch) -> None:
    scraper = FourChanScraper()
    catalog_data = [
        {"threads": [{"no": 1}, {"no": 2}]},
        {"threads": [{"no": 3}, {"no": 4}]},
    ]
    monkeypatch.setattr(scraper, "get_catalog_data", lambda board: catalog_data)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    scraped_threads: list[str] = []

    def fake_scrape_thread(board: str, thread_id: str):
        scraped_threads.append(thread_id)
        media = MediaFile(
            f"https://i.4cdn.org/{board}/{thread_id}.jpg",
            f"{thread_id}.jpg",
            board=board,
            thread_id=thread_id,
        )
        return [media], f"Thread {thread_id}"

    monkeypatch.setattr(scraper, "scrape_thread", fake_scrape_thread)

    media_files = scraper.scrape_catalog("g", max_threads=2)

    assert scraped_threads == ["1", "2"]
    assert len(media_files) == 2
    assert {media.thread_id for media in media_files} == {"1", "2"}


def test_scrape_catalog_returns_empty_when_catalog_missing(monkeypatch) -> None:
    scraper = FourChanScraper()
    monkeypatch.setattr(scraper, "get_catalog_data", lambda board: None)

    assert scraper.scrape_catalog("g", max_threads=5) == []


def test_get_thread_data_attaches_extracted_title(monkeypatch) -> None:
    scraper = FourChanScraper()
    response = Mock()
    response.json.return_value = {
        "posts": [{"sub": "OP title", "tim": 1, "ext": ".jpg", "filename": "a"}],
    }
    response.raise_for_status = Mock()

    monkeypatch.setattr(
        scraper._board_api,
        "fetch_thread",
        lambda board, thread_id: response,
    )
    monkeypatch.setattr(scraper, "adaptive_delay", lambda success=False: None)

    thread_data = scraper.get_thread_data("g", "42")

    assert thread_data is not None
    assert thread_data["_thread_title"] == "OP title"
