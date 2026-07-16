"""User-facing error formatting and classification.

Owns two responsibilities that previously lived on ``FourChanScraper``:
  - ``format_error_message``: turn a raw ``requests`` / ``OSError`` exception
    into a user-friendly message with actionable guidance
  - ``handle_network_error``: classify the error into a ``category`` (rate
    limit / access / connection / timeout / http / redirects / unknown) and
    return a dict the GUI can inspect

The ErrorFormatter keeps no state of its own — it just shapes exceptions.
``FourChanScraper`` owns the rate-limit delay (delegated to ``RetryPolicy``).
"""

from __future__ import annotations

import logging
from typing import Any

import requests


logger = logging.getLogger("4Charm")


class ErrorFormatter:
    """Format and classify network/OS errors for the user and the GUI."""

    @staticmethod
    def format_error_message(error: Exception, context: dict) -> str:
        """Build a user-facing error message from ``error`` and ``context``.

        ``context`` may contain ``url``, ``filename``, ``timeout``,
        ``retry_delay``, ``required_mb``, ``available_mb``, ``path``.
        """
        filename = context.get("filename", "file")

        if isinstance(error, requests.exceptions.ConnectionError):
            return f"Connection failed for {filename}. Check your internet connection."

        if isinstance(error, requests.exceptions.Timeout):
            timeout = context.get("timeout", "unknown")
            return (
                f"Download timed out after {timeout}s for {filename}. "
                "The server may be slow or unresponsive."
            )

        if isinstance(error, requests.exceptions.HTTPError):
            status = getattr(error.response, "status_code", 0)
            if status == 403:
                return (
                    f"Access denied for {filename}. The file may have been "
                    "deleted or is no longer available."
                )
            if status == 404:
                return (
                    f"File not found: {filename}. The thread may have been "
                    "archived or deleted."
                )
            if status == 429:
                delay = context.get("retry_delay", "unknown")
                return (
                    f"Rate limited by server for {filename}. "
                    f"Waiting {delay}s before retry."
                )
            return f"HTTP {status} error for {filename}. {error!s}"

        if isinstance(error, OSError):
            error_str = str(error)
            if "No space left" in error_str or "Disk quota exceeded" in error_str:
                required = context.get("required_mb", "unknown")
                available = context.get("available_mb", "unknown")
                return (
                    f"Insufficient disk space. "
                    f"Need {required}MB, have {available}MB free."
                )
            if "Permission denied" in error_str:
                path = context.get("path", "unknown")
                return f"Cannot write to {path}. Check folder permissions."
            return f"File system error for {filename}: {error!s}"

        return f"Error downloading {filename}: {error!s}"

    def classify(
        self,
        error: Exception,
        *,
        url: str,
        context: str = "",
        filename: str = "",
        retry_delay_for_rate_limit: float | None = None,
    ) -> dict[str, Any]:
        """Classify ``error`` and return a dict the GUI can inspect.

        The optional ``retry_delay_for_rate_limit`` is a pre-computed backoff
        in seconds; when provided, the rate-limit message reflects it. The
        ``category`` key is one of: ``rate_limited``, ``access``,
        ``connection``, ``timeout``, ``http``, ``redirects``, ``unknown``.
        """
        error_info: dict[str, Any] = {
            "type": type(error).__name__,
            "message": str(error),
            "url": url,
            "context": context,
        }

        error_context = {
            "url": url,
            "filename": filename or url.split("/")[-1],
            "timeout": None,
        }

        if isinstance(error, requests.exceptions.ConnectionError):
            friendly = self.format_error_message(error, error_context)
            logger.error(friendly)
            error_info["category"] = "connection"
            error_info["friendly_message"] = friendly
            return error_info

        if isinstance(error, requests.exceptions.Timeout):
            friendly = self.format_error_message(error, error_context)
            logger.error(friendly)
            error_info["category"] = "timeout"
            error_info["friendly_message"] = friendly
            return error_info

        if isinstance(error, requests.exceptions.HTTPError):
            status_code = getattr(error.response, "status_code", 0)
            error_info["status_code"] = status_code
            if status_code == 429:
                if retry_delay_for_rate_limit is not None:
                    error_context["retry_delay"] = f"{retry_delay_for_rate_limit:.1f}"
                friendly = self.format_error_message(error, error_context)
                logger.warning(friendly)
                error_info["category"] = "rate_limited"
                error_info["friendly_message"] = friendly
                return error_info

            friendly = self.format_error_message(error, error_context)
            logger.error(friendly)
            if status_code in (403, 404):
                error_info["category"] = "access"
            else:
                error_info["category"] = "http"
            error_info["friendly_message"] = friendly
            return error_info

        if isinstance(error, requests.exceptions.TooManyRedirects):
            logger.error(f"Too many redirects {context} for {url}: {error!s}")
            error_info["category"] = "redirects"
            return error_info

        friendly = self.format_error_message(error, error_context)
        logger.error(f"{friendly} {context} for {url}")
        error_info["category"] = "unknown"
        error_info["friendly_message"] = friendly
        return error_info
