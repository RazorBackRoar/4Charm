from unittest.mock import Mock

from four_charm.core.scraper import FourChanScraper


class FakeBoardApi:
    """Minimal BoardApi fake for scraper fetch tests."""

    def __init__(self) -> None:
        self.fetch_thread_calls: list[tuple[str, str]] = []
        self.fetch_catalog_calls: list[str] = []

    def fetch_thread(self, board: str, thread_id: str):
        self.fetch_thread_calls.append((board, thread_id))
        response = Mock()
        response.json.return_value = {
            "posts": [{"no": 123, "com": "Thread title"}],
        }
        response.raise_for_status.return_value = None
        return response

    def fetch_catalog(self, board: str):
        self.fetch_catalog_calls.append(board)
        response = Mock()
        response.json.return_value = [{"threads": []}]
        response.raise_for_status.return_value = None
        return response

    def stream_range(self, url, *, headers=None, timeout=None):
        raise NotImplementedError


def test_scraper_initialization():
    scraper = FourChanScraper()
    assert scraper is not None


def test_parse_thread_url_valid():
    url = "https://boards.4chan.org/g/thread/12345678"
    scraper = FourChanScraper()
    result = scraper.parse_url(url)
    assert result is not None
    assert result["board"] == "g"
    assert result["thread_id"] == "12345678"
    assert result["type"] == "thread"


def test_parse_thread_url_invalid():
    url = "https://google.com"
    scraper = FourChanScraper()
    assert scraper.parse_url(url) is None


def test_get_thread_data_uses_board_api_and_adds_title():
    api = FakeBoardApi()
    scraper = FourChanScraper(board_api=api)

    data = scraper.get_thread_data("g", "123")

    assert data is not None
    assert data["posts"][0]["no"] == 123
    assert data["_thread_title"] == "Thread title"
    assert api.fetch_thread_calls == [("g", "123")]


def test_get_catalog_data_uses_board_api():
    api = FakeBoardApi()
    scraper = FourChanScraper(board_api=api)

    data = scraper.get_catalog_data("wsg")

    assert data == [{"threads": []}]
    assert api.fetch_catalog_calls == ["wsg"]
