"""HTTP session factory for 4chan API and media downloads.

Creates a pre-configured requests session with connection pooling,
retry logic, and standard headers. No Qt dependencies.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter

import four_charm.config as config
from four_charm.core.urls import is_allowed_fetch_host


MAX_REDIRECTS = 5
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


def create_session() -> requests.Session:
    """Create a pre-configured HTTP session with optimized connection pooling.

    Uses 4x multiplier for pool sizing to support concurrent downloads efficiently.
    Retries are handled manually in the scraper for better control.
    """
    session = requests.Session()

    # Enhanced pool sizing: 4x workers for better concurrency
    pool_size = config.MAX_WORKERS * config.POOL_CONNECTIONS_MULTIPLIER

    adapter = HTTPAdapter(
        pool_connections=pool_size,
        pool_maxsize=pool_size,
        max_retries=0,  # Handle retries manually for better control
        pool_block=False,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json, text/html, */*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "DNT": "1",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    return session


def _resolve_redirect_url(
    session: requests.Session, url: str, **kwargs: Any
) -> tuple[str, requests.Response | None]:
    """Follow redirects manually, validating each hop stays on allowed hosts."""
    probe_kwargs = dict(kwargs)
    probe_kwargs.pop("stream", None)
    probe_kwargs["allow_redirects"] = False

    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        response = session.get(current_url, stream=False, **probe_kwargs)
        if response.status_code not in _REDIRECT_STATUSES:
            return current_url, response

        location = response.headers.get("Location")
        response.close()
        if not location:
            return current_url, None

        next_url = urljoin(current_url, location)
        next_host = urlparse(next_url).hostname
        if not is_allowed_fetch_host(next_host):
            raise requests.exceptions.RequestException(
                f"Blocked redirect to disallowed host: {next_url}"
            )
        current_url = next_url

    raise requests.exceptions.TooManyRedirects(
        f"Exceeded {MAX_REDIRECTS} redirects for {url}"
    )


def safe_get(session: requests.Session, url: str, **kwargs: Any) -> requests.Response:
    """GET with manual redirect handling and per-hop host allowlisting."""
    stream = bool(kwargs.get("stream"))
    final_url, resolved = _resolve_redirect_url(session, url, **kwargs)
    if resolved is not None and not stream:
        return resolved

    if resolved is not None:
        resolved.close()

    fetch_kwargs = dict(kwargs)
    fetch_kwargs["allow_redirects"] = False
    return session.get(final_url, **fetch_kwargs)
