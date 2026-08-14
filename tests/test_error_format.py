"""Tests for ErrorFormatter classification used by scraper retry logic."""

import requests

from four_charm.core.error_format import ErrorFormatter


def _http_error(status_code: int) -> requests.exceptions.HTTPError:
    error = requests.exceptions.HTTPError(f"HTTP {status_code}")
    error.response = type("MockResponse", (), {"status_code": status_code})()
    return error


def test_classify_marks_429_as_rate_limited() -> None:
    formatter = ErrorFormatter()
    info = formatter.classify(
        _http_error(429),
        url="https://a.4cdn.org/g/thread/1.json",
        filename="1.jpg",
        retry_delay_for_rate_limit=4.0,
    )

    assert info["category"] == "rate_limited"
    assert "Rate limited" in info["friendly_message"]
    assert "4.0" in info["friendly_message"]


def test_classify_marks_403_and_404_as_access() -> None:
    formatter = ErrorFormatter()

    forbidden = formatter.classify(
        _http_error(403),
        url="https://i.4cdn.org/g/1.jpg",
        filename="1.jpg",
    )
    missing = formatter.classify(
        _http_error(404),
        url="https://i.4cdn.org/g/2.jpg",
        filename="2.jpg",
    )

    assert forbidden["category"] == "access"
    assert missing["category"] == "access"
    assert "Access denied" in forbidden["friendly_message"]
    assert "File not found" in missing["friendly_message"]


def test_classify_marks_other_http_as_http_category() -> None:
    formatter = ErrorFormatter()
    info = formatter.classify(
        _http_error(500),
        url="https://i.4cdn.org/g/1.jpg",
        filename="1.jpg",
    )

    assert info["category"] == "http"
    assert info["status_code"] == 500


def test_classify_marks_redirect_loops() -> None:
    formatter = ErrorFormatter()
    info = formatter.classify(
        requests.exceptions.TooManyRedirects("too many"),
        url="https://i.4cdn.org/g/loop.jpg",
        context="streaming media",
    )

    assert info["category"] == "redirects"


def test_handle_network_error_doubles_delay_on_rate_limit(monkeypatch) -> None:
    from four_charm.core.scraper import FourChanScraper

    scraper = FourChanScraper()
    scraper._retry_policy.current_delay = 2.0
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    info = scraper.handle_network_error(
        _http_error(429),
        url="https://a.4cdn.org/g/thread/1.json",
        filename="1.jpg",
    )

    assert info["category"] == "rate_limited"
    assert scraper._retry_policy.current_delay == 4.0
