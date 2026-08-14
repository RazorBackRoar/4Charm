"""Tests for LiveBoardApi URL construction and streaming options."""

from unittest.mock import MagicMock, patch

from four_charm.transport.api import LiveBoardApi


def test_live_board_api_fetch_thread_builds_catalog_url() -> None:
    session = MagicMock()
    api = LiveBoardApi(session)

    with patch("four_charm.transport.api.safe_get") as mock_safe_get:
        api.fetch_thread("g", "123456")

    mock_safe_get.assert_called_once_with(
        session,
        "https://a.4cdn.org/g/thread/123456.json",
        timeout=mock_safe_get.call_args.kwargs.get("timeout"),
    )


def test_live_board_api_fetch_catalog_builds_catalog_url() -> None:
    session = MagicMock()
    api = LiveBoardApi(session)

    with patch("four_charm.transport.api.safe_get") as mock_safe_get:
        api.fetch_catalog("g")

    mock_safe_get.assert_called_once_with(
        session,
        "https://a.4cdn.org/g/catalog.json",
        timeout=mock_safe_get.call_args.kwargs.get("timeout"),
    )


def test_live_board_api_stream_range_uses_streaming_get() -> None:
    session = MagicMock()
    api = LiveBoardApi(session)
    headers = {"Range": "bytes=10-"}

    with patch("four_charm.transport.api.safe_get") as mock_safe_get:
        api.stream_range("https://i.4cdn.org/g/1.jpg", headers=headers)

    mock_safe_get.assert_called_once()
    call_kwargs = mock_safe_get.call_args.kwargs
    assert call_kwargs["stream"] is True
    assert call_kwargs["headers"] == headers
    assert call_kwargs["timeout"] is not None
