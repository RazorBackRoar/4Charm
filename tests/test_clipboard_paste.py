"""Clipboard paste and drop formatting behavior for URL input."""

from four_charm.gui.main_window import (
    _append_urls_to_input,
    _format_clipboard_paste_text,
    _is_4chan_host,
)


def test_is_4chan_host_accepts_allowed_domains() -> None:
    """Accept canonical 4chan hosts including www and 4channel."""
    assert _is_4chan_host("https://boards.4chan.org/g/thread/123")
    assert _is_4chan_host("https://www.4chan.org/")
    assert _is_4chan_host("https://4channel.org/")


def test_is_4chan_host_rejects_spoofed_hostnames() -> None:
    """Reject hosts that only contain 4chan as a substring."""
    assert not _is_4chan_host("https://not4chan.org/boards.4chan.org/g/thread/123")
    assert not _is_4chan_host("https://4chan.org.evil.com/")


def test_paste_format_always_appends_newline() -> None:
    """Ensure paste content ends on a new line."""
    result = _format_clipboard_paste_text(
        "https://boards.4chan.org/g/thread/123", position_in_block=0
    )
    assert result == "https://boards.4chan.org/g/thread/123\n"


def test_paste_format_adds_leading_newline_mid_line() -> None:
    """When cursor is mid-line, start pasted content on the next line."""
    result = _format_clipboard_paste_text(
        "https://boards.4chan.org/g/thread/123", position_in_block=5
    )
    assert result == "\nhttps://boards.4chan.org/g/thread/123\n"


def test_paste_format_adds_leading_newline_at_start_of_nonempty_line() -> None:
    """When cursor is at col 0 on a non-empty line, keep paste on the next line."""
    result = _format_clipboard_paste_text(
        "https://boards.4chan.org/g/thread/123",
        position_in_block=0,
        current_block_text="existing text on line",
    )
    assert result == "\nhttps://boards.4chan.org/g/thread/123\n"


def test_paste_format_filters_urls_and_preserves_newline() -> None:
    """Extract and keep only valid 4chan URLs when URLs are present."""
    raw = (
        "https://not4chan.org/thread/1\n"
        "https://boards.4chan.org/g/thread/2\n"
        "https://4channel.org/v/thread/3"
    )
    result = _format_clipboard_paste_text(raw, position_in_block=0)
    assert result == (
        "https://boards.4chan.org/g/thread/2\nhttps://4channel.org/v/thread/3\n"
    )


def test_paste_format_keeps_raw_text_when_no_urls() -> None:
    """If no URLs exist, preserve text and still end with a newline."""
    result = _format_clipboard_paste_text("just plain text", position_in_block=0)
    assert result == "just plain text\n"


def test_append_urls_to_input_preserves_existing_and_incoming_order() -> None:
    """Dropping URLs should append, never replace, and preserve drop ordering."""
    existing = "https://boards.4chan.org/g/thread/300\nhttps://boards.4chan.org/v/thread/100"
    incoming = (
        "random text\nhttps://boards.4chan.org/a/thread/900\n"
        "https://boards.4chan.org/g/thread/200"
    )
    result = _append_urls_to_input(existing, incoming)
    assert result == (
        "https://boards.4chan.org/g/thread/300\n"
        "https://boards.4chan.org/v/thread/100\n"
        "https://boards.4chan.org/a/thread/900\n"
        "https://boards.4chan.org/g/thread/200"
    )


def test_append_urls_to_input_ignores_non_4chan_drop_text() -> None:
    """Invalid dropped text should not clear existing URLs."""
    existing = "https://boards.4chan.org/g/thread/300"
    incoming = "https://example.com/not-valid"
    assert _append_urls_to_input(existing, incoming) == existing
