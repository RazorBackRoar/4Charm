from __future__ import annotations

import re

from PySide6.QtCore import QMimeData, Qt, QTimer
from PySide6.QtGui import QColor, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
)


_URL_PATTERN = re.compile(r"https?://[^\s<>\'\"]+")


def apply_neon_glow(widget, color="#3fe469", blur=14):
    """Apply a neon drop-shadow glow to a widget."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setColor(QColor(color))
    effect.setOffset(0, 0)
    widget.setGraphicsEffect(effect)


class NeonPanel(QFrame):
    def __init__(self, object_name: str = "NeonPanel") -> None:
        super().__init__()
        self.setObjectName(object_name)
        apply_neon_glow(self, "#3fe469", 18)


class NeonButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class StatCard(QFrame):
    def __init__(self, label: str, value: str, icon: str = "") -> None:
        super().__init__()
        self.setObjectName("StatCard")
        apply_neon_glow(self, "#3fe469", 12)
        self.setFixedHeight(38)

        icon_label = QLabel(icon)
        icon_label.setObjectName("StatIcon")
        icon_label.setFixedWidth(24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(label)
        title.setObjectName("StatLabel")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)
        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class ActivityLog(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ActivityLog")
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def add_line(self, text: str) -> None:
        self.appendPlainText(text)
        self.moveCursor(QTextCursor.MoveOperation.End)


class UrlInputEdit(QPlainTextEdit):
    """URL text editor that auto-parses pasted URLs into separate lines."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._line_fmt: QTextBlockFormat | None = None

    def insertFromMimeData(self, source: QMimeData) -> None:
        if source.hasText():
            text = source.text()
            matches = _URL_PATTERN.findall(text)
            if matches:
                super().insertPlainText("\n".join(matches) + "\n")
            else:
                super().insertPlainText(text)
            self._apply_block_format_to_all()
        else:
            super().insertFromMimeData(source)

    def set_line_block_format(self, fmt: QTextBlockFormat) -> None:
        self._line_fmt = fmt

    def _apply_block_format_to_all(self) -> None:
        if not self._line_fmt:
            return
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(self._line_fmt)


class LineNumberTextEdit(QFrame):
    """Composite widget: line-number gutter + URL text editor."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("UrlInputFrame")

        # --- Line number gutter ---
        self.line_numbers = QPlainTextEdit(self)
        self.line_numbers.setObjectName("LineNumbers")
        self.line_numbers.setReadOnly(True)
        self.line_numbers.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.line_numbers.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        self.line_numbers.setFrameStyle(QFrame.Shape.NoFrame)
        self.line_numbers.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.line_numbers.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.line_numbers.setFixedWidth(44)
        self.line_numbers.document().setDocumentMargin(0)
        self.line_numbers.setPlainText("1")

        self._line_fmt = QTextBlockFormat()
        self._line_fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._line_fmt.setLineHeight(
            140.0, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
        )
        cursor = self.line_numbers.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(self._line_fmt)

        # --- Main editor ---
        self.editor = UrlInputEdit(self)
        self.editor.setObjectName("UrlEditor")
        self.editor.setPlaceholderText("Paste thread URLs here...")
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.editor.document().setDocumentMargin(0)

        self._url_input_fmt = QTextBlockFormat()
        self._url_input_fmt.setLineHeight(
            140.0, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
        )
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(self._url_input_fmt)
        self.editor.set_line_block_format(self._url_input_fmt)

        # --- Layout ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.line_numbers)
        layout.addWidget(self.editor)

        # --- Scroll synchronization ---
        self.editor.textChanged.connect(self.update_line_numbers)
        self.editor.verticalScrollBar().valueChanged.connect(
            self.line_numbers.verticalScrollBar().setValue
        )
        self.editor.verticalScrollBar().rangeChanged.connect(
            self._sync_line_numbers_scroll
        )
        self.line_numbers.verticalScrollBar().rangeChanged.connect(
            self._sync_line_numbers_scroll
        )

    def _sync_line_numbers_scroll(self, *_args) -> None:
        """Keep line-number gutter scrollbar locked to the editor scrollbar."""
        self.line_numbers.verticalScrollBar().setValue(
            self.editor.verticalScrollBar().value()
        )

    def update_line_numbers(self) -> None:
        text = self.editor.toPlainText()
        count = max(1, text.count("\n") + 1)
        self.line_numbers.setPlainText(
            "\n".join(str(i) for i in range(1, count + 1))
        )
        # Re-apply centre-aligned block format after text replacement
        cursor = self.line_numbers.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(self._line_fmt)
        # setPlainText resets the scrollbar — defer sync to after layout finishes
        QTimer.singleShot(0, self._sync_line_numbers_scroll)

    def urls(self) -> list[str]:
        return [
            line.strip()
            for line in self.editor.toPlainText().splitlines()
            if line.strip()
        ]

    def clear(self) -> None:
        self.editor.clear()

    def focus_input(self) -> None:
        self.editor.setFocus()
        self.editor.moveCursor(QTextCursor.MoveOperation.End)
