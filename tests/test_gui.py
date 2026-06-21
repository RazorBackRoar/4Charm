"""Focused GUI behavior tests for the 4Charm main window."""

from __future__ import annotations

import os
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def _app() -> QApplication:
    existing = QApplication.instance()
    if existing is None:
        return QApplication([])
    return cast(QApplication, existing)


def test_paste_urls_use_four_visually_spaced_slots() -> None:
    """Four pasted URLs should stay four real lines with four visible slots."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()
    urls = [
        "https://boards.4chan.org/g/thread/1",
        "https://boards.4chan.org/g/thread/2",
        "https://boards.4chan.org/g/thread/3",
        "https://boards.4chan.org/g/thread/4",
    ]

    try:
        app.clipboard().setText(" ".join(urls))
        window.paste_from_clipboard()

        assert window.url_input.toPlainText() == "\n\n".join(urls)
        assert window.url_input.document().blockCount() == 7
        assert window.url_input_frame.urls() == urls
        assert window.url_count_label.text() == "QUEUE: 4"
        assert window.line_numbers.toPlainText() == "\n\n".join(
            str(number) for number in range(1, 5)
        )
    finally:
        window.deleteLater()
        app.processEvents()


def test_url_input_scrolls_after_large_plain_text_paste() -> None:
    """The URL box should behave like a normal scrolling editor for 20 lines."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()
    window.resize(1100, 700)
    window.show()
    app.processEvents()

    urls = [
        f"https://boards.4chan.org/g/thread/{number}" for number in range(1, 21)
    ]
    paste_text = " ".join(urls)
    expected_text = "\n\n".join(urls)

    try:
        app.clipboard().setText(paste_text)
        window.url_input.setFocus()
        window.paste_from_clipboard()

        for _ in range(6):
            app.processEvents()

        scrollbar = window.url_input.verticalScrollBar()

        assert window.url_input.toPlainText() == expected_text
        assert window.url_input.document().blockCount() == 39
        assert window.line_numbers.toPlainText() == "\n\n".join(
            str(number) for number in range(1, 21)
        )
        assert window.url_input.verticalScrollBarPolicy() == (
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        assert scrollbar.maximum() > 0
        # In offscreen mode, deferred ensureCursorVisible timers may leave the
        # scroll position 1-2px short of the absolute maximum.  Accept "near
        # the bottom" as proof that scrolling is working correctly.
        assert scrollbar.value() >= scrollbar.maximum() - 2
    finally:
        window.deleteLater()
        app.processEvents()


def test_url_scrollbar_starts_after_four_urls() -> None:
    """Four URL slots should fit; the fifth should enable mouse-wheel scrolling."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()
    window.show()

    try:
        four_urls = " ".join(
            f"https://boards.4chan.org/g/thread/{number}" for number in range(1, 5)
        )
        app.clipboard().setText(four_urls)
        window.paste_from_clipboard()
        app.processEvents()

        assert window.url_input.verticalScrollBar().maximum() == 0

        window.url_input.clear()
        five_urls = " ".join(
            f"https://boards.4chan.org/g/thread/{number}" for number in range(1, 6)
        )
        app.clipboard().setText(five_urls)
        window.paste_from_clipboard()
        app.processEvents()

        assert window.url_input.verticalScrollBar().maximum() > 0
        assert window.url_input.verticalScrollBarPolicy() == (
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
    finally:
        window.deleteLater()
        app.processEvents()


def test_start_button_updates_ready_state_immediately() -> None:
    """Start styling and icon should update as URL validity changes."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()

    try:
        idle_icon_key = window.start_cancel_btn.icon().cacheKey()
        assert window.start_cancel_btn.property("ready") is False
        assert not window.start_cancel_btn.isEnabled()

        window.url_input.setPlainText("https://boards.4chan.org/g/thread/1")
        app.processEvents()

        ready_icon_key = window.start_cancel_btn.icon().cacheKey()
        assert window.start_cancel_btn.property("ready") is True
        assert window.start_cancel_btn.isEnabled()
        assert ready_icon_key != idle_icon_key

        window.url_input.clear()
        app.processEvents()

        assert window.start_cancel_btn.property("ready") is False
        assert not window.start_cancel_btn.isEnabled()
        assert window.start_cancel_btn.icon().cacheKey() != ready_icon_key
    finally:
        window.deleteLater()
        app.processEvents()


def test_enter_creates_new_line_and_updates_gutter() -> None:
    """Pressing Enter should create a new line and update line numbers."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()

    try:
        # Type a URL then press Enter
        window.url_input.setPlainText("https://boards.4chan.org/g/thread/1")
        app.processEvents()

        # Move cursor to end and simulate Enter
        cursor = window.url_input.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        window.url_input.setTextCursor(cursor)

        enter_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        window.url_input.keyPressEvent(enter_event)
        app.processEvents()

        assert window.url_input.document().blockCount() == 3
        assert window.line_numbers.toPlainText() == "\n\n".join(
            str(number) for number in range(1, 5)
        )

        # Type a second URL
        window.url_input.insertPlainText("https://boards.4chan.org/g/thread/2")
        app.processEvents()

        assert window.url_input.document().blockCount() == 3
        assert window.line_numbers.toPlainText() == "\n\n".join(
            str(number) for number in range(1, 5)
        )
        assert window.url_count_label.text() == "QUEUE: 2"
    finally:
        window.deleteLater()
        app.processEvents()


def test_premium_idle_ui_contract() -> None:
    """The idle UI should expose polished labels and the approved initial stats."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()

    try:
        assert window.start_cancel_btn.text() == "Start Download"
        assert window.clear_btn.text() == "Clear"
        assert window.folder_btn.text() == "Folder"
        assert window.pause_resume_btn.text() == "Pause"
        assert window.progress_label.text() == "Ready"
        assert window.folders_card.value_label.text() == "0"
        assert window.files_card.value_label.text() == "0"
        assert window.storage_card.value_label.text() == "0.0GB"
        assert window.status_message.text() == "Engine Status: Ready"
    finally:
        window.deleteLater()
        app.processEvents()


def test_lower_area_places_stats_to_the_right_of_log() -> None:
    """Layout A should use a wide log with a vertical stats rail."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()

    try:
        assert isinstance(window.lower_layout, QHBoxLayout)
        assert isinstance(window.stats_layout, QVBoxLayout)
        assert window.lower_layout.indexOf(window.log_panel) == 0
        assert window.lower_layout.indexOf(window.stats_panel) == 1
        assert window.stats_layout.indexOf(window.folders_card) == 0
        assert window.stats_layout.indexOf(window.files_card) == 1
        assert window.stats_layout.indexOf(window.storage_card) == 2
    finally:
        window.deleteLater()
        app.processEvents()


def test_reference_visual_details_are_present() -> None:
    """The premium UI should include clean icons, startup activity, and status dot."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()

    try:
        assert not window.start_cancel_btn.icon().isNull()
        assert not window.clear_btn.icon().isNull()
        assert not window.folder_btn.icon().isNull()
        assert window.status_indicator.objectName() == "StatusIndicator"
        assert window.status_indicator.size().width() == 10

        log_text = window.log_text.toPlainText()
        assert "Engine initialized" in log_text
        assert "Ready to download..." in log_text
        assert "All systems operational" in log_text
        assert "Queue is empty" in log_text
    finally:
        window.deleteLater()
        app.processEvents()


def test_reference_action_and_gutter_proportions() -> None:
    """Action buttons and the empty URL gutter should match the reference."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from four_charm.gui.main_window import MainWindow

    app = _app()
    window = MainWindow()
    window.show()
    app.processEvents()

    try:
        assert window.start_cancel_btn.height() == 44
        assert window.clear_btn.height() == 44
        assert window.folder_btn.height() == 44
        assert window.line_numbers.width() == 60
        assert window.line_numbers.toPlainText() == "\n\n".join(
            str(number) for number in range(1, 5)
        )
        assert window.line_numbers.document().defaultTextOption().alignment() == (
            Qt.AlignmentFlag.AlignCenter
        )
        assert window.url_input_frame.minimumHeight() == 142
        assert window.url_input_frame.maximumHeight() == 142
        assert (
            window.url_input_frame.geometry().bottom()
            < window.start_cancel_btn.geometry().top()
        )
        assert window.stats_panel.width() == 350
        assert window.folders_card.height() == 50
        assert window.files_card.height() == 50
        assert window.storage_card.height() == 50
        assert window.minimumSize().width() == 960
        assert window.minimumSize().height() == 640
        assert window.size().width() == 1080
        assert window.size().height() == 680
        assert window.status_bar.height() <= 40
        assert window.windowTitle() == ""
    finally:
        window.deleteLater()
        app.processEvents()
