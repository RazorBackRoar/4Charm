
from unittest.mock import Mock, patch

from four_charm.core.scraper import FourChanScraper


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

@patch("requests.Session.get")
def test_fetch_thread_data_success(mock_get):
    mock_response = Mock()
    mock_response.json.return_value = {"posts": [{"no": 123}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    scraper = FourChanScraper()
    data = scraper.get_thread_data("g", "123")
    assert data is not None
    assert data["posts"][0]["no"] == 123
