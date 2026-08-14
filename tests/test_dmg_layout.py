"""Pin 4Charm's DMG artwork to the locked no-scrollbar Finder window."""

from __future__ import annotations

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "assets" / "dmg-layout.json"
BACKGROUND_PATH = ROOT / "assets" / "dmg-background.png"
BACKGROUND_2X_PATH = ROOT / "assets" / "dmg-background@2x.png"

LOCKED_WINDOW = (500, 420)
LOCKED_WINDOW_2X = (1000, 840)
LOCKED_APP_POS = (130, 160)
LOCKED_APPS_POS = (370, 160)
ICON_SIZE = 128
LABEL_BUDGET = 28


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def test_dmg_background_matches_locked_window() -> None:
    """1x art is 500×420; @2x fills the same window on Retina (no white strip)."""
    assert BACKGROUND_PATH.is_file()
    assert _png_size(BACKGROUND_PATH) == LOCKED_WINDOW
    assert BACKGROUND_2X_PATH.is_file()
    assert _png_size(BACKGROUND_2X_PATH) == LOCKED_WINDOW_2X


def test_dmg_icon_positions_match_locked_layout() -> None:
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    assert tuple(layout["app_pos"]) == LOCKED_APP_POS
    assert tuple(layout["apps_pos"]) == LOCKED_APPS_POS
    assert layout["background"] == "assets/dmg-background.png"


def test_dmg_icons_fit_inside_window_without_scroll() -> None:
    """Icon + label must stay inside the 420px window even with Finder chrome."""
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    half = ICON_SIZE // 2
    for key in ("app_pos", "apps_pos"):
        x, y = layout[key]
        assert 0 < x < LOCKED_WINDOW[0]
        assert y - half >= 0
        assert y + half + LABEL_BUDGET <= LOCKED_WINDOW[1]
