"""Tests for the LiveBoardApi transport seam."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import four_charm.config as config
from four_charm.transport.api import LiveBoardApi


def test_live_board_api_fetch_thread_uses_safe_get() -> None:
    session = MagicMock()
    api = LiveBoardApi(session)
    expected = MagicMock()

    with patch(
        "four_charm.transport.api.safe_get", return_value=expected
    ) as mock_safe_get:
        response = api.fetch_thread("g", "123456")

    assert response is expected
    mock_safe_get.assert_called_once_with(
        session,
        "https://a.4cdn.org/g/thread/123456.json",
        timeout=config.API_TIMEOUT,
    )


def test_live_board_api_fetch_catalog_uses_safe_get() -> None:
    session = MagicMock()
    api = LiveBoardApi(session)
    expected = MagicMock()

    with patch(
        "four_charm.transport.api.safe_get", return_value=expected
    ) as mock_safe_get:
        response = api.fetch_catalog("wsg")

    assert response is expected
    mock_safe_get.assert_called_once_with(
        session,
        "https://a.4cdn.org/wsg/catalog.json",
        timeout=config.API_TIMEOUT,
    )


def test_live_board_api_stream_range_passes_stream_and_headers() -> None:
    session = MagicMock()
    api = LiveBoardApi(session)
    headers = {"Range": "bytes=0-"}
    expected = MagicMock()

    with patch(
        "four_charm.transport.api.safe_get", return_value=expected
    ) as mock_safe_get:
        response = api.stream_range(
            "https://i.4cdn.org/g/1.jpg",
            headers=headers,
            timeout=(10, 30),
        )

    assert response is expected
    mock_safe_get.assert_called_once_with(
        session,
        "https://i.4cdn.org/g/1.jpg",
        headers=headers,
        stream=True,
        timeout=(10, 30),
    )


def test_live_board_api_stream_range_uses_download_timeout_by_default() -> None:
    session = MagicMock()
    api = LiveBoardApi(session)

    with patch("four_charm.transport.api.safe_get", return_value=MagicMock()) as mock_safe_get:
        api.stream_range("https://i.4cdn.org/g/1.jpg")

    assert mock_safe_get.call_args.kwargs["timeout"] == config.DOWNLOAD_TIMEOUT
