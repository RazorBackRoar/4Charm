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


def test_paste_urls_one_per_line_without_hidden_blank_line() -> None:
    """Pasted thread URLs should produce visible 1..N line numbering."""
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

        assert window.url_input.toPlainText() == "\n".join(urls)
        assert window.line_numbers.toPlainText() == "1\n2\n3\n4"
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

    paste_text = "\n".join(str(i) for i in range(1, 21))

    try:
        app.clipboard().setText(paste_text)
        window.url_input.setFocus()
        window.paste_from_clipboard()

        for _ in range(6):
            app.processEvents()

        scrollbar = window.url_input.verticalScrollBar()

        assert window.url_input.toPlainText() == paste_text
        assert window.url_input.document().blockCount() == 20
        assert window.line_numbers.toPlainText() == paste_text
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

        assert window.url_input.document().blockCount() == 2
        assert window.line_numbers.toPlainText() == "1\n2"

        # Type a second URL
        window.url_input.insertPlainText("https://boards.4chan.org/g/thread/2")
        app.processEvents()

        assert window.url_input.document().blockCount() == 2
        assert window.line_numbers.toPlainText() == "1\n2"
        assert window.url_count_label.text() == "QUEUE: 2"
    finally:
        window.deleteLater()
        app.processEvents()
