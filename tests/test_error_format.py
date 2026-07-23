"""Tests for ErrorFormatter classification and user-facing messages."""

from __future__ import annotations

import requests

from four_charm.core.error_format import ErrorFormatter


def _http_error(status_code: int) -> requests.exceptions.HTTPError:
    class MockResponse:
        pass

    response = MockResponse()
    response.status_code = status_code
    error = requests.exceptions.HTTPError(f"HTTP {status_code}")
    error.response = response  # ty: ignore[invalid-assignment]
    return error


def test_classify_connection_error() -> None:
    formatter = ErrorFormatter()
    error = requests.exceptions.ConnectionError("refused")

    info = formatter.classify(
        error,
        url="https://i.4cdn.org/g/1.jpg",
        filename="1.jpg",
    )

    assert info["category"] == "connection"
    assert "friendly_message" in info
    assert "Connection failed" in info["friendly_message"]
    assert info["url"] == "https://i.4cdn.org/g/1.jpg"


def test_classify_timeout_error() -> None:
    formatter = ErrorFormatter()
    error = requests.exceptions.Timeout("timed out")

    info = formatter.classify(error, url="https://i.4cdn.org/g/1.jpg")

    assert info["category"] == "timeout"
    assert "timed out" in info["friendly_message"].lower()


def test_classify_rate_limited_includes_retry_delay() -> None:
    formatter = ErrorFormatter()
    error = _http_error(429)

    info = formatter.classify(
        error,
        url="https://a.4cdn.org/g/catalog.json",
        filename="catalog.json",
        retry_delay_for_rate_limit=4.5,
    )

    assert info["category"] == "rate_limited"
    assert info["status_code"] == 429
    assert "4.5" in info["friendly_message"]
    assert "Rate limited" in info["friendly_message"]


def test_classify_access_errors_for_403_and_404() -> None:
    formatter = ErrorFormatter()

    for status in (403, 404):
        info = formatter.classify(
            _http_error(status),
            url=f"https://i.4cdn.org/g/{status}.jpg",
            filename=f"{status}.jpg",
        )
        assert info["category"] == "access"
        assert info["status_code"] == status


def test_classify_generic_http_error() -> None:
    formatter = ErrorFormatter()
    info = formatter.classify(
        _http_error(500),
        url="https://i.4cdn.org/g/1.jpg",
        filename="1.jpg",
    )

    assert info["category"] == "http"
    assert info["status_code"] == 500
    assert "HTTP 500" in info["friendly_message"]


def test_classify_too_many_redirects() -> None:
    formatter = ErrorFormatter()
    error = requests.exceptions.TooManyRedirects("loop")

    info = formatter.classify(
        error,
        url="https://i.4cdn.org/g/1.jpg",
        context="streaming media",
    )

    assert info["category"] == "redirects"
    assert "friendly_message" not in info


def test_classify_unknown_error_falls_back_to_generic_message() -> None:
    formatter = ErrorFormatter()
    error = RuntimeError("unexpected")

    info = formatter.classify(
        error,
        url="https://i.4cdn.org/g/1.jpg",
        filename="1.jpg",
    )

    assert info["category"] == "unknown"
    assert "Error downloading 1.jpg" in info["friendly_message"]
