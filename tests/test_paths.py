"""Tests for the PathBuilder (filesystem seam to razorcore)."""

from __future__ import annotations

from pathlib import Path

import pytest

import four_charm.config as config
from four_charm.core.models import MediaFile
from four_charm.core.paths import (
    PathBuilder,
    limit_folder_length,
    sanitize_filename,
    sanitize_folder_component,
)


def test_sanitize_filename_respects_max_length() -> None:
    long_name = "x" * (config.MAX_FILENAME_LENGTH + 50) + ".jpg"
    sanitized = sanitize_filename(long_name)

    assert len(sanitized) <= config.MAX_FILENAME_LENGTH
    assert sanitized.endswith(".jpg")


def test_sanitize_folder_component_strips_dot_segments() -> None:
    assert sanitize_folder_component("..") == "session"
    assert sanitize_folder_component("") == "session"
    assert sanitize_folder_component("a..b") == "a_b"
    assert sanitize_folder_component("normal/folder") == "normal_folder"
    assert sanitize_folder_component("  leading-trailing  . ") == "leading-trailing"
    assert sanitize_folder_component("name?with*chars") == "name_with_chars"


def test_path_builder_raises_without_download_dir(tmp_path: Path) -> None:
    builder = PathBuilder()
    with pytest.raises(ValueError, match="Download directory not set"):
        builder.within_download_dir(tmp_path / "x")


def test_path_builder_within_download_dir_allows_inside(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    builder = PathBuilder(root)
    target = root / "inside.txt"

    resolved = builder.within_download_dir(target)
    assert resolved.is_relative_to(root.resolve())


def test_path_builder_rejects_outside_target(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.touch()

    builder = PathBuilder(root)
    with pytest.raises(ValueError, match="outside download directory"):
        builder.within_download_dir(outside)


def test_path_builder_build_creates_thread_and_webm_subdirs(tmp_path: Path) -> None:
    builder = PathBuilder(tmp_path)
    media = MediaFile("https://i.4cdn.org/g/123.webm", "123.webm")

    file_path, save_dir = builder.build(media, "g-thread")

    assert file_path.parent == save_dir
    assert save_dir.name == "WEBM"
    assert file_path.is_relative_to(tmp_path)


def test_path_builder_build_flattens_parent_segments(tmp_path: Path) -> None:
    builder = PathBuilder(tmp_path)
    media = MediaFile("https://i.4cdn.org/g/123.jpg", "123.jpg")

    file_path, save_dir = builder.build(media, "../escape")

    assert file_path.is_relative_to(tmp_path)
    assert ".." not in str(save_dir)


def test_path_builder_session_base_name_includes_thread_id() -> None:
    builder = PathBuilder()
    name = builder.session_base_name(
        {"board": "g", "type": "thread", "thread_id": "123"}
    )
    assert name == "g-123"


def test_path_builder_thread_folder_name_prefers_title() -> None:
    builder = PathBuilder()
    name = builder.thread_folder_name("Hello world", "123", "g")
    assert name == "Hello world"


def test_path_builder_thread_folder_name_falls_back_to_id() -> None:
    builder = PathBuilder()
    name = builder.thread_folder_name(None, "123", "g")
    assert name == "g-123"


def test_limit_folder_length_truncates_and_strips_trailing_separators() -> None:
    long_name = "a" * (config.MAX_FOLDER_NAME_LENGTH + 20) + "---"
    trimmed = limit_folder_length(long_name)

    assert len(trimmed) <= config.MAX_FOLDER_NAME_LENGTH
    assert not trimmed.endswith("-")
    assert trimmed == "a" * config.MAX_FOLDER_NAME_LENGTH


def test_limit_folder_length_returns_session_for_empty_result() -> None:
    assert limit_folder_length("") == "session"


def test_path_builder_session_base_name_catalog() -> None:
    builder = PathBuilder()
    name = builder.session_base_name({"board": "g", "type": "catalog", "thread_id": None})
    assert name == "g-catalog"


def test_path_builder_session_base_name_empty_board_fallback() -> None:
    builder = PathBuilder()
    name = builder.session_base_name({"board": "", "type": "board", "thread_id": None})
    assert name == "4chan"
