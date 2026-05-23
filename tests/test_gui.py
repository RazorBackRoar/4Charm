"""Focused GUI behavior tests for the 4Charm main window."""

from __future__ import annotations

import os


def test_paste_urls_one_per_line_without_hidden_blank_line() -> None:
    """Pasted thread URLs should produce visible 1..N line numbering."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from four_charm.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
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
        assert window.url_input.minimumHeight() >= 220
    finally:
        window.close()


def test_url_input_scrolls_to_newest_line_after_large_plain_text_paste() -> None:
    """The URL box should behave like a normal scrolling editor for 20 lines."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from four_charm.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
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
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        assert scrollbar.maximum() > 0
        assert scrollbar.value() == scrollbar.maximum()
    finally:
        window.close()
