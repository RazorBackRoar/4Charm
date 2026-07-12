"""URL extraction and validation helpers for 4chan links."""

from __future__ import annotations

import re
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")
_TRAILING_PUNCT = re.compile(r"[.,;:)\]}>]+$")

ALLOWED_HOST_SUFFIXES = (".4chan.org", ".4channel.org")
ALLOWED_FETCH_SUFFIXES = (".4chan.org", ".4channel.org", ".4cdn.org")
ALLOWED_EXACT_HOSTS = frozenset(
    {
        "4chan.org",
        "4channel.org",
        "boards.4chan.org",
        "boards.4channel.org",
        "a.4cdn.org",
        "i.4cdn.org",
        "is2.4chan.org",
        "is2.4channel.org",
    }
)

MAX_QUEUE_URLS = 50


def normalize_host(hostname: str | None) -> str:
    return (hostname or "").lower().rstrip(".")


def is_allowed_4chan_host(hostname: str | None) -> bool:
    """Return True when the host is a known 4chan/4channel CDN or board host."""
    host = normalize_host(hostname)
    if not host:
        return False
    if host in ALLOWED_EXACT_HOSTS:
        return True
    return any(host.endswith(suffix) for suffix in ALLOWED_HOST_SUFFIXES)


def is_allowed_fetch_host(hostname: str | None) -> bool:
    """Return True for outbound fetch/redirect targets (includes 4cdn API hosts)."""
    host = normalize_host(hostname)
    if not host:
        return False
    if host in ALLOWED_EXACT_HOSTS:
        return True
    return any(host.endswith(suffix) for suffix in ALLOWED_FETCH_SUFFIXES)


def clean_url_token(url: str) -> str:
    """Strip whitespace and trailing punctuation from a pasted URL token."""
    cleaned = url.strip()
    cleaned = _TRAILING_PUNCT.sub("", cleaned)
    if cleaned and not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned


def extract_url_tokens(text: str) -> list[str]:
    """Extract URL-like tokens from arbitrary pasted or dropped text."""
    if not text or not text.strip():
        return []

    tokens = [clean_url_token(match) for match in URL_PATTERN.findall(text)]
    tokens = [token for token in tokens if token]

    if tokens:
        return tokens

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        cleaned = clean_url_token(line)
        if cleaned:
            tokens.append(cleaned)
    return tokens


def filter_supported_urls(urls: list[str]) -> list[str]:
    """Keep only URLs hosted on supported 4chan domains."""
    supported: list[str] = []
    for url in urls:
        try:
            hostname = urlparse(url).hostname
        except ValueError:
            continue
        if is_allowed_4chan_host(hostname):
            supported.append(url)
    return supported


def dedupe_preserve_order(urls: list[str]) -> list[str]:
    """Remove duplicate URLs while preserving first-seen order."""
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        key = url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(url)
    return unique


def extract_supported_4chan_urls(text: str) -> list[str]:
    """Extract, sanitize, and dedupe supported 4chan URLs from pasted text."""
    return dedupe_preserve_order(filter_supported_urls(extract_url_tokens(text)))


def format_urls_for_editor(urls: list[str]) -> str:
    """Join URLs using the editor's visual spacing convention."""
    return "\n\n".join(urls)
