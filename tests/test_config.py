"""Tests for user configuration validation and loading."""

import json
from pathlib import Path

import pytest

from four_charm.config import Config


def _bare_config() -> Config:
    """Config instance without reading the real user config file."""
    cfg = Config.__new__(Config)
    cfg._initialized = True
    return cfg


def test_validate_config_accepts_values_within_range() -> None:
    cfg = _bare_config()
    user_config = {"MAX_RETRIES": 5, "RATE_LIMIT_DELAY": 1.5}

    cfg._validate_config(user_config)

    assert user_config["MAX_RETRIES"] == 5
    assert user_config["RATE_LIMIT_DELAY"] == 1.5


def test_validate_config_rejects_max_workers_out_of_range() -> None:
    cfg = _bare_config()

    with pytest.raises(ValueError, match="MAX_WORKERS"):
        cfg._validate_config({"MAX_WORKERS": 99})


def test_validate_config_rejects_invalid_type() -> None:
    cfg = _bare_config()

    with pytest.raises(ValueError, match="Invalid value for CHUNK_SIZE"):
        cfg._validate_config({"CHUNK_SIZE": "not-a-number"})


def test_load_config_returns_empty_on_corrupt_json(tmp_path: Path) -> None:
    cfg = _bare_config()
    bad_path = tmp_path / "config.json"
    bad_path.write_text("{not-json", encoding="utf-8")
    cfg._config_path = bad_path

    assert cfg._load_config() == {}


def test_load_config_reads_valid_user_overrides(tmp_path: Path) -> None:
    cfg = _bare_config()
    good_path = tmp_path / "config.json"
    good_path.write_text(json.dumps({"MAX_RETRIES": 4}), encoding="utf-8")
    cfg._config_path = good_path

    user_config = cfg._load_config()

    assert user_config["MAX_RETRIES"] == 4


def test_apply_config_merges_user_values_over_defaults() -> None:
    cfg = _bare_config()
    cfg._user_config = {"MAX_RETRIES": 7, "API_TIMEOUT": 45}
    cfg._apply_config()

    assert cfg.MAX_RETRIES == 7
    assert cfg.API_TIMEOUT == 45
    assert cfg.CHUNK_SIZE == Config._DEFAULTS["CHUNK_SIZE"]


def test_reload_config_reapplies_file_overrides(tmp_path: Path) -> None:
    cfg = _bare_config()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"MAX_RETRIES": 2}), encoding="utf-8")
    cfg._config_path = config_path
    cfg._user_config = {}
    cfg._apply_config()
    assert cfg.MAX_RETRIES == Config._DEFAULTS["MAX_RETRIES"]

    config_path.write_text(json.dumps({"MAX_RETRIES": 6}), encoding="utf-8")
    cfg.reload_config()

    assert cfg.MAX_RETRIES == 6
