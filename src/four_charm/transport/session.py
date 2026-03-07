"""HTTP session factory for 4chan API and media downloads.

Creates a pre-configured requests session with connection pooling,
retry logic, and standard headers. No Qt dependencies.
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter

from four_charm.config import Config


def create_session() -> requests.Session:
    """Create a pre-configured HTTP session with retry and pooling."""
    session = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=Config.MAX_WORKERS * 2,
        pool_maxsize=Config.MAX_WORKERS * 2,
        max_retries=Config.MAX_RETRIES,
        pool_block=False,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": Config.USER_AGENT,
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
