from __future__ import annotations

from PySide6.QtCore import (
    QMimeData,
    QPointF,
    QRectF,
    QSignalBlocker,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QIcon,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
)

from four_charm.core.urls import extract_supported_4chan_urls, format_urls_for_editor


def create_interface_icon(kind: str, color: str = "#f5f7f5", size: int = 24) -> QIcon:
    """Create a simple monochrome interface icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), max(1.5, size * 0.075))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    scale = float(size)
    if kind == "play":
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(scale * 0.34, scale * 0.22),
                    QPointF(scale * 0.76, scale * 0.50),
                    QPointF(scale * 0.34, scale * 0.78),
                ]
            )
        )
    elif kind == "pause":
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            QRectF(scale * 0.29, scale * 0.22, scale * 0.13, scale * 0.56),
            scale * 0.04,
            scale * 0.04,
        )
        painter.drawRoundedRect(
            QRectF(scale * 0.58, scale * 0.22, scale * 0.13, scale * 0.56),
            scale * 0.04,
            scale * 0.04,
        )
    elif kind == "cancel":
        painter.drawLine(
            QPointF(scale * 0.27, scale * 0.27),
            QPointF(scale * 0.73, scale * 0.73),
        )
        painter.drawLine(
            QPointF(scale * 0.73, scale * 0.27),
            QPointF(scale * 0.27, scale * 0.73),
        )
    elif kind == "trash":
        painter.drawRoundedRect(
            QRectF(scale * 0.29, scale * 0.31, scale * 0.42, scale * 0.50),
            scale * 0.05,
            scale * 0.05,
        )
        painter.drawLine(
            QPointF(scale * 0.23, scale * 0.27),
            QPointF(scale * 0.77, scale * 0.27),
        )
        painter.drawLine(
            QPointF(scale * 0.40, scale * 0.19),
            QPointF(scale * 0.60, scale * 0.19),
        )
        painter.drawLine(
            QPointF(scale * 0.43, scale * 0.42),
            QPointF(scale * 0.43, scale * 0.68),
        )
        painter.drawLine(
            QPointF(scale * 0.57, scale * 0.42),
            QPointF(scale * 0.57, scale * 0.68),
        )
    elif kind == "folder":
        path = QPainterPath()
        path.moveTo(scale * 0.16, scale * 0.31)
        path.lineTo(scale * 0.40, scale * 0.31)
        path.lineTo(scale * 0.49, scale * 0.40)
        path.lineTo(scale * 0.84, scale * 0.40)
        path.lineTo(scale * 0.78, scale * 0.76)
        path.lineTo(scale * 0.20, scale * 0.76)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "file":
        path = QPainterPath()
        path.moveTo(scale * 0.28, scale * 0.16)
        path.lineTo(scale * 0.61, scale * 0.16)
        path.lineTo(scale * 0.76, scale * 0.31)
        path.lineTo(scale * 0.76, scale * 0.84)
        path.lineTo(scale * 0.28, scale * 0.84)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(
            QPointF(scale * 0.61, scale * 0.17),
            QPointF(scale * 0.61, scale * 0.32),
        )
        painter.drawLine(
            QPointF(scale * 0.61, scale * 0.32),
            QPointF(scale * 0.75, scale * 0.32),
        )
        painter.drawLine(
            QPointF(scale * 0.39, scale * 0.55),
            QPointF(scale * 0.65, scale * 0.55),
        )
        painter.drawLine(
            QPointF(scale * 0.39, scale * 0.68),
            QPointF(scale * 0.61, scale * 0.68),
        )
    elif kind == "drive":
        painter.drawRoundedRect(
            QRectF(scale * 0.17, scale * 0.25, scale * 0.66, scale * 0.52),
            scale * 0.08,
            scale * 0.08,
        )
        painter.drawLine(
            QPointF(scale * 0.23, scale * 0.57),
            QPointF(scale * 0.77, scale * 0.57),
        )
        painter.setBrush(QColor(color))
        painter.drawEllipse(
            QPointF(scale * 0.31, scale * 0.67),
            scale * 0.035,
            scale * 0.035,
        )
        painter.drawEllipse(
            QPointF(scale * 0.42, scale * 0.67),
            scale * 0.035,
            scale * 0.035,
        )

    painter.end()

    icon = QIcon()
    for mode in (
        QIcon.Mode.Normal,
        QIcon.Mode.Disabled,
        QIcon.Mode.Active,
        QIcon.Mode.Selected,
    ):
        icon.addPixmap(pixmap, mode)
    return icon


class NeonPanel(QFrame):
    def __init__(self, object_name: str = "NeonPanel") -> None:
        super().__init__()
        self.setObjectName(object_name)


class NeonButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class StatCard(QFrame):
    def __init__(self, label: str, value: str, icon: QIcon | None = None) -> None:
        super().__init__()
        self.setObjectName("StatCard")
        self.setFixedHeight(50)

        title = QLabel(label)
        title.setObjectName("StatLabel")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("StatValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 5, 9, 5)
        layout.setSpacing(7)
        if icon is not None:
            icon_label = QLabel()
            icon_label.setObjectName("StatIcon")
            icon_label.setFixedSize(28, 28)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setPixmap(icon.pixmap(QSize(22, 22)))
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
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not self.document().isEmpty():
            cursor.insertBlock()

        line_format = QTextCharFormat()
        success_terms = ("complete", "downloaded", "ready", "success", "operational")
        color = "#65e37b" if any(term in text.lower() for term in success_terms) else "#d8ddda"
        line_format.setForeground(QColor(color))
        cursor.setCharFormat(line_format)
        cursor.insertText(text)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()


class UrlInputEdit(QPlainTextEdit):
    """URL text editor that auto-parses pasted URLs into separate lines."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._line_fmt: QTextBlockFormat | None = None

    def insertFromMimeData(self, source: QMimeData) -> None:
        if source.hasText():
            text = source.text()
            urls = extract_supported_4chan_urls(text)
            if urls:
                super().insertPlainText(format_urls_for_editor(urls))
            else:
                super().insertPlainText(text)
            self.apply_line_block_format()
        else:
            super().insertFromMimeData(source)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.insertText("\n\n")
            self.setTextCursor(cursor)
            self.apply_line_block_format()
            return
        super().keyPressEvent(event)

    def set_line_block_format(self, fmt: QTextBlockFormat) -> None:
        self._line_fmt = fmt

    def apply_line_block_format(self) -> None:
        if not self._line_fmt:
            return
        blocker = QSignalBlocker(self.document())
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(self._line_fmt)
        del blocker


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
        self.line_numbers.setFixedWidth(60)
        self.line_numbers.document().setDocumentMargin(0)
        text_option = self.line_numbers.document().defaultTextOption()
        text_option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_numbers.document().setDefaultTextOption(text_option)
        self.line_numbers.setPlainText(
            "\n\n".join(str(number) for number in range(1, 5))
        )

        self._line_fmt = QTextBlockFormat()
        self._line_fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(self._url_input_fmt)
        self.editor.set_line_block_format(self._url_input_fmt)

        # --- Layout ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 6)
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
        self.editor.apply_line_block_format()
        count = max(4, len(self.urls()))
        self.line_numbers.setPlainText(
            "\n\n".join(str(i) for i in range(1, count + 1))
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
