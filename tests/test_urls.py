"""Tests for centralized 4chan URL helpers."""

from four_charm.core.urls import (
    MAX_QUEUE_URLS,
    clean_url_token,
    dedupe_preserve_order,
    extract_supported_4chan_urls,
    is_allowed_4chan_host,
)


def test_extract_supported_urls_from_safari_style_batch() -> None:
    text = " ".join(
        f"https://boards.4chan.org/g/thread/{number},"
        for number in range(1, 6)
    )
    urls = extract_supported_4chan_urls(text)

    assert len(urls) == 5
    assert urls[0] == "https://boards.4chan.org/g/thread/1"
    assert urls[-1] == "https://boards.4chan.org/g/thread/5"


def test_extract_supported_urls_rejects_spoofed_hosts() -> None:
    text = "https://evil.example/4chan.org/g/thread/1 https://boards.4chan.org/g/thread/2"
    urls = extract_supported_4chan_urls(text)

    assert urls == ["https://boards.4chan.org/g/thread/2"]


def test_extract_supported_urls_accepts_4channel_and_media_hosts() -> None:
    text = "\n".join(
        [
            "https://boards.4channel.org/g/thread/99",
            "https://i.4cdn.org/g/12345.jpg",
        ]
    )
    urls = extract_supported_4chan_urls(text)

    assert urls == [
        "https://boards.4channel.org/g/thread/99",
        "https://i.4cdn.org/g/12345.jpg",
    ]


def test_clean_url_token_strips_trailing_punctuation() -> None:
    assert (
        clean_url_token("https://boards.4chan.org/g/thread/1).")
        == "https://boards.4chan.org/g/thread/1"
    )


def test_dedupe_preserve_order_is_case_insensitive_for_path() -> None:
    urls = dedupe_preserve_order(
        [
            "https://boards.4chan.org/g/thread/1",
            "https://boards.4chan.org/g/thread/1/",
            "https://boards.4chan.org/g/thread/2",
        ]
    )

    assert urls == [
        "https://boards.4chan.org/g/thread/1",
        "https://boards.4chan.org/g/thread/2",
    ]


def test_is_allowed_4chan_host_uses_real_hostnames() -> None:
    assert is_allowed_4chan_host("boards.4chan.org")
    assert is_allowed_4chan_host("i.4cdn.org")
    assert not is_allowed_4chan_host("not4chan.org")


def test_max_queue_urls_is_generous_for_batch_paste() -> None:
    assert MAX_QUEUE_URLS >= 50
