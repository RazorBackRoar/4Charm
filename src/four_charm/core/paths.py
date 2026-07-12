"""Download path construction and sanitization.

Centralizes all filesystem path logic for 4Charm downloads:
  - Filename sanitization (delegated to razorcore with 4Charm max-length)
  - Folder-name sanitization (inline rules for parent directory segments)
  - Per-folder layout (WEBM subfolder, parent-segment flattening)
  - Download-dir containment (resolved-path assertion)

The single PathBuilder is the seam to razorcore.filesystem; a different
downloader can swap the implementation as long as it honours the same
``build`` / ``within_download_dir`` contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import four_charm.config as config
from razorcore.filesystem import sanitize_filename as _rc_sanitize


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Sanitize a download filename through razorcore (keeps 4Charm max length).

    Public seam to ``razorcore.filesystem.sanitize_filename``. The max-length
    is bound to ``config.MAX_FILENAME_LENGTH`` so user config changes flow
    through automatically.
    """
    return _rc_sanitize(
        name,
        max_length=config.MAX_FILENAME_LENGTH,
        replacement=replacement,
    )


def sanitize_folder_component(name: str) -> str:
    """Sanitize a name used as a folder (parent segment) under the download root.

    Rules diverge from ``sanitize_filename`` because folder names need to
    drop trailing dots/spaces and dot-segments (``..``) before path assembly.
    Returns ``"session"`` when the input collapses to empty.
    """
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or "")
    sanitized = sanitized.replace("..", "_")
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    sanitized = sanitized.strip("-_ ")
    return sanitized or "session"


def limit_folder_length(name: str, max_length: int | None = None) -> str:
    """Trim a folder name to ``config.MAX_FOLDER_NAME_LENGTH`` (or override)."""
    cap = max_length if max_length is not None else config.MAX_FOLDER_NAME_LENGTH
    if len(name) > cap:
        name = name[:cap].rstrip("-_ ")
    return name or "session"


class PathBuilder:
    """Builds and validates download paths under a single download root.

    One PathBuilder per ``FourChanScraper`` instance, holding the current
    ``download_dir``. Constructing a new PathBuilder resets the bound root;
    it does not own any state that would need to migrate between runs.
    """

    def __init__(self, download_dir: Path | None = None) -> None:
        self.download_dir = download_dir

    def set_download_dir(self, download_dir: Path) -> None:
        """Set or replace the bound download root."""
        self.download_dir = download_dir

    def within_download_dir(self, target: Path) -> Path:
        """Return ``target`` resolved only when it stays inside ``download_dir``.

        Raises ``ValueError`` when the download root is unset or the resolved
        target would escape it. The resolved path is the canonical form
        callers should use for I/O.
        """
        if self.download_dir is None:
            raise ValueError("Download directory not set")

        base = self.download_dir.resolve()
        resolved = target.resolve()
        try:
            resolved.relative_to(base)
        except ValueError as exc:
            raise ValueError(
                f"Refusing to write outside download directory: {target}"
            ) from exc
        return resolved

    def build(
        self, media_file, url_folder_name: str | None
    ) -> tuple[Path, Path]:
        """Return ``(file_path, save_dir)`` for a media file under the root.

        Creates the parent directory when it does not yet exist. ``.webm``
        files are routed into a ``WEBM/`` subfolder. The folder name is
        sanitized via ``sanitize_folder_component`` so parent-segments in
        the source thread title cannot escape the download root.
        """
        if self.download_dir is None:
            raise ValueError("Download directory not set")

        folder_name = sanitize_folder_component(url_folder_name or "misc")
        thread_dir = self.download_dir / folder_name
        self.within_download_dir(thread_dir)
        thread_dir.mkdir(parents=True, exist_ok=True)

        if media_file.filename.lower().endswith(".webm"):
            save_dir = thread_dir / "WEBM"
            self.within_download_dir(save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = thread_dir

        file_path = save_dir / sanitize_filename(media_file.filename)
        self.within_download_dir(file_path)
        return file_path, save_dir

    # ------------------------------------------------------------------
    # Session / thread folder naming
    # ------------------------------------------------------------------
    def session_base_name(self, parsed_url: dict) -> str:
        """Build the base folder name for a parsed 4chan URL."""
        board = parsed_url.get("board", "").strip()
        url_type = parsed_url.get("type")
        thread_id = parsed_url.get("thread_id")
        if url_type == "thread" and thread_id:
            base_name = f"{board}-{thread_id}"
        elif url_type == "catalog":
            base_name = f"{board}-catalog"
        else:
            base_name = board or "4chan"
        return limit_folder_length(sanitize_folder_component(base_name))

    def thread_folder_name(
        self, thread_title: str | None, thread_id: str, board: str
    ) -> str:
        """Build a folder name for a thread (title preferred, fallback to id)."""
        if thread_title and thread_title.strip():
            folder_name = sanitize_folder_component(thread_title)
            folder_name = limit_folder_length(folder_name)
            if folder_name:
                return folder_name
        return f"{board}-{thread_id}"
