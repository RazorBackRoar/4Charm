"""HTTP session factory for 4chan API and media downloads.

Creates a pre-configured requests session with connection pooling,
retry logic, and standard headers. No Qt dependencies.
"""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter

import four_charm.config as config


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
