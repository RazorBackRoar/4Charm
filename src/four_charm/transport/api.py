"""Board API seam for 4chan fetches.

The ``BoardApi`` Protocol is the boundary between the scraper and the network.
The scraper depends on the protocol; the live ``LiveBoardApi`` adapter is the
only thing that talks to ``a.4cdn.org`` / ``i.4cdn.org`` and follows the
manual redirect rules from ``four_charm.transport.session``.

Tests inject a fake ``BoardApi``; production runs use ``LiveBoardApi``. The
Protocol deliberately exposes only fetch primitives (``fetch_thread``,
``fetch_catalog``, ``stream_range``) so the scraper stops naming the
transport implementation in its public surface.

Errors propagate as ``requests`` exceptions — the scraper (via
``ErrorFormatter``) owns classification and retry decisions, not the transport.
"""

from __future__ import annotations

from typing import Protocol

import requests

import four_charm.config as config
from four_charm.transport.session import safe_get


class BoardApi(Protocol):
    """Protocol for 4chan board/media network access.

    Any class that implements these three methods can be passed to
    ``FourChanScraper`` in place of ``LiveBoardApi``. Returned ``Response``
    objects follow the ``requests`` contract; the scraper treats them as
    opaque handles.
    """

    def fetch_thread(self, board: str, thread_id: str) -> requests.Response:
        """Fetch a thread JSON. Raises ``requests`` exceptions on failure."""
        ...

    def fetch_catalog(self, board: str) -> requests.Response:
        """Fetch a board catalog JSON. Raises ``requests`` exceptions on failure."""
        ...

    def stream_range(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: tuple[int, int] | None = None,
    ) -> requests.Response:
        """Open a streaming GET for a media URL (resumable via Range header)."""
        ...


class LiveBoardApi:
    """Concrete ``BoardApi`` that talks to ``a.4cdn.org`` and ``i.4cdn.org``.

    The session is shared with the scraper so connection pooling and
    rate-limit headers are reused across catalog, thread, and media fetches.
    """

    def __init__(self, session: requests.Session) -> None:
        self._session = session

    def fetch_thread(self, board: str, thread_id: str) -> requests.Response:
        """Fetch a thread JSON; raises ``requests`` exceptions on failure."""
        url = f"https://a.4cdn.org/{board}/thread/{thread_id}.json"
        return safe_get(self._session, url, timeout=config.API_TIMEOUT)

    def fetch_catalog(self, board: str) -> requests.Response:
        """Fetch a board catalog JSON; raises ``requests`` exceptions on failure."""
        url = f"https://a.4cdn.org/{board}/catalog.json"
        return safe_get(self._session, url, timeout=config.API_TIMEOUT)

    def stream_range(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: tuple[int, int] | None = None,
    ) -> requests.Response:
        """Open a streaming GET for a media URL (Range header for resume)."""
        return safe_get(
            self._session,
            url,
            headers=headers,
            stream=True,
            timeout=timeout or config.DOWNLOAD_TIMEOUT,
        )
