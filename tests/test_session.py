"""Tests for redirect-safe HTTP session helpers."""

from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
import requests

from four_charm.core.urls import is_allowed_fetch_host
from four_charm.transport.session import MAX_REDIRECTS, safe_get


def test_is_allowed_fetch_host_includes_4cdn_api() -> None:
    assert is_allowed_fetch_host("a.4cdn.org")
    assert is_allowed_fetch_host("i.4cdn.org")
    assert is_allowed_fetch_host("boards.4chan.org")
    assert not is_allowed_fetch_host("evil.com")


def test_safe_get_blocks_disallowed_redirect() -> None:
    session = requests.Session()

    redirect_response = MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {"Location": "https://evil.com/secret"}
    redirect_response.close = MagicMock()

    with patch.object(session, "get", return_value=redirect_response) as mock_get:
        with pytest.raises(requests.exceptions.RequestException, match="Blocked redirect"):
            safe_get(session, "https://i.4cdn.org/g/1.jpg", timeout=5)

    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs.get("allow_redirects") is False


def test_safe_get_follows_allowed_redirect() -> None:
    session = requests.Session()

    redirect_response = MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {
        "Location": "https://i.4cdn.org/g/redirected.jpg",
    }
    redirect_response.close = MagicMock()

    final_response = MagicMock()
    final_response.status_code = 200
    final_response.headers = {"content-length": "3"}

    with patch.object(
        session, "get", side_effect=[redirect_response, final_response]
    ) as mock_get:
        response = safe_get(session, "https://i.4cdn.org/g/1.jpg", timeout=5)

    assert response is final_response
    assert mock_get.call_count == 2
    redirect_host = urlparse("https://i.4cdn.org/g/redirected.jpg").hostname
    assert is_allowed_fetch_host(redirect_host)
    assert mock_get.call_args_list[1].kwargs.get("allow_redirects") is False


def test_safe_get_raises_too_many_redirects_on_redirect_loop() -> None:
    session = requests.Session()

    def make_redirect_response() -> MagicMock:
        response = MagicMock()
        response.status_code = 302
        response.headers = {"Location": "https://i.4cdn.org/g/next.jpg"}
        response.close = MagicMock()
        return response

    redirect_chain = [make_redirect_response() for _ in range(MAX_REDIRECTS + 1)]

    with patch.object(session, "get", side_effect=redirect_chain):
        with pytest.raises(requests.exceptions.TooManyRedirects, match="Exceeded"):
            safe_get(session, "https://i.4cdn.org/g/1.jpg", timeout=5)


def test_safe_get_retries_without_location_header() -> None:
    session = requests.Session()

    redirect_response = MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {}
    redirect_response.close = MagicMock()

    final_response = MagicMock()
    final_response.status_code = 200

    with patch.object(
        session, "get", side_effect=[redirect_response, final_response]
    ) as mock_get:
        response = safe_get(session, "https://i.4cdn.org/g/1.jpg", timeout=5)

    assert response is final_response
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[1].args[0] == "https://i.4cdn.org/g/1.jpg"
