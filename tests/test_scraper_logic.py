
import pytest
from unittest.mock import Mock, patch
from four_charm.core.scraper import Scraper

def test_scraper_initialization():
    scraper = Scraper()
    assert scraper is not None

def test_parse_thread_url_valid():
    url = "https://boards.4chan.org/g/thread/12345678"
    from four_charm.core.scraper import parse_thread_url
    board, thread_id = parse_thread_url(url)
    assert board == "g"
    assert thread_id == "12345678"

def test_parse_thread_url_invalid():
    url = "https://google.com"
    from four_charm.core.scraper import parse_thread_url
    assert parse_thread_url(url) is None

@patch("requests.get")
def test_fetch_thread_data_success(mock_get):
    mock_response = Mock()
    mock_response.json.return_value = {"posts": [{"no": 123}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    from four_charm.core.scraper import fetch_thread_data
    data = fetch_thread_data("g", 123)
    assert data == {"posts": [{"no": 123}]}
