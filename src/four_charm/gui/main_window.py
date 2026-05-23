# ##############################################################################
# #                   HOW LINE NUMBERS STAY SYNCHRONIZED                         #
# ##############################################################################
#
# ## The Magic Behind Real-Time Updates
#
# The dynamic line numbering happens in the validate_urls method, which is connected
# to the URL input's textChanged signal. Every time you press Enter, the code
# immediately recalculates the number of lines and updates the display on the left side.
#
# ## Synchronization Flow
#
# ```mermaid
# graph TD
#     A[User types URL / Enter] -->|textChanged signal| B[validate_urls Method]
#     B --> C[1. Count Newlines (\n)]
#     C --> D[2. Generate Number Sequence]
#     D --> E[Update line_numbers Display]
#     E --> F[3. Synchronize Vertical Scrollbars]
#     F --> G[Pixel Perfect UI Alignment]
# end
# ```
#
# ---
#
# ## The Three-Step Process
#
# ### 1. Counting the Lines
# When you press Enter, it creates a newline character (\n). The code splits the
# text by this character to determine how many lines currently exist:
#
# raw_text = self.url_input.toPlainText()
# all_lines = raw_text.split("\n")
# line_count = max(1, len(all_lines))
#
# ### 2. Generating the Number Sequence
# Once we have the count, we build a string of numbers from 1 through N:
#
# line_nums = "\n".join(str(i) for i in range(1, line_count + 1))
# self.line_numbers.setPlainText(line_nums)
#
# ### 3. Keeping Everything Synchronized
# To ensure the line numbers stay perfectly aligned (especially when scrolling),
# we synchronize the scrollbars:
#
# current_scroll = self.url_input.verticalScrollBar().value()
# self.line_numbers.verticalScrollBar().setValue(current_scroll)
#
# ---

import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import override

from PySide6.QtCore import QMimeData, Qt, QThread, QTimer
from PySide6.QtGui import (
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
    QShortcut,
    QTextBlockFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from four_charm.core.scraper import FourChanScraper
from four_charm.gui.workers import MultiUrlDownloadWorker


logger = logging.getLogger("4Charm")


_URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+")


def _is_supported_4chan_url(url: str) -> bool:
    return "boards.4chan.org" in url or "4channel.org" in url or "4chan.org" in url


def _extract_supported_urls(text: str) -> list[str]:
    """Return supported 4chan URLs from pasted or dropped text."""
    urls = []
    for match in _URL_PATTERN.findall(text):
        url = match.rstrip(".,;:)]}")
        if _is_supported_4chan_url(url):
            urls.append(url)
    return urls


def _build_url_paste_text(
    text_before_cursor: str, text_after_cursor: str, urls: list[str]
) -> str:
    paste_text = "\n".join(urls)
    if text_before_cursor and not text_before_cursor.endswith("\n"):
        paste_text = "\n" + paste_text
    if text_after_cursor and not text_after_cursor.startswith("\n"):
        paste_text += "\n"
    return paste_text


def _insert_url_lines(editor: QPlainTextEdit, urls: list[str]) -> None:
    cursor = editor.textCursor()
    existing_text = editor.toPlainText()
    start = cursor.selectionStart()
    end = cursor.selectionEnd()
    paste_text = _build_url_paste_text(existing_text[:start], existing_text[end:], urls)
    cursor.insertText(paste_text)
    editor.setTextCursor(cursor)
    editor.ensureCursorVisible()
    QTimer.singleShot(0, editor.ensureCursorVisible)


class UrlInputEdit(QPlainTextEdit):
    """URL editor that normalizes pasted thread lists before insertion."""

    @override
    def insertFromMimeData(self, source: QMimeData) -> None:
        if source.hasText():
            urls = _extract_supported_urls(source.text())
            if urls:
                _insert_url_lines(self, urls)
                return

        super().insertFromMimeData(source)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("")
        self.setMinimumSize(1100, 700)
        self.resize(1100, 700)
        self.setAcceptDrops(True)

        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #0f0f0f;
                color: #e0e0e0;
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif;
            }
            QWidget#centralWidget {
                border-top: 1px solid rgba(118, 230, 72, 0.2);
            }

            /* Card Containers */
            QFrame#urlMasterContainer, QGroupBox {
                border: 1px solid rgba(118, 230, 72, 0.2);
                border-radius: 10px;
                background-color: rgba(30, 30, 30, 0.4);
                margin-top: 10px;
            }

            QFrame#editorSurface {
                background-color: rgba(0, 0, 0, 0.24);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #76e648;
                font-size: 11px;
                font-weight: 800;
                background-color: transparent;
                letter-spacing: 1px;
            }

            QLabel#urlSectionTitle {
                color: #76e648;
                font-size: 11px;
                font-weight: 800;
                padding: 12px 15px;
                letter-spacing: 1px;
            }

            /* Input Fields */
            QPlainTextEdit, QTextEdit {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                font-size: 13px;
                selection-background-color: rgba(118, 230, 72, 0.4);
            }

            QPlainTextEdit#urlInput {
                color: #f3f6f0;
                padding: 10px 6px 10px 0px;
            }

            QPlainTextEdit#lineNumberGutter {
                color: rgba(118, 230, 72, 0.62);
                padding: 10px 0px;
                selection-background-color: transparent;
                selection-color: rgba(118, 230, 72, 0.62);
            }

            QTextEdit#logView {
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 6px;
            }

            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.04);
                border: none;
                border-radius: 5px;
                width: 10px;
                margin: 4px 2px 4px 0px;
            }

            QScrollBar::handle:vertical {
                background: rgba(118, 230, 72, 0.42);
                border-radius: 5px;
                min-height: 28px;
            }

            QScrollBar::handle:vertical:hover {
                background: rgba(118, 230, 72, 0.62);
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
                height: 0px;
            }

            QScrollBar:horizontal {
                background: rgba(255, 255, 255, 0.04);
                border: none;
                border-radius: 5px;
                height: 10px;
                margin: 0px 4px 2px 0px;
            }

            QScrollBar::handle:horizontal {
                background: rgba(118, 230, 72, 0.36);
                border-radius: 5px;
                min-width: 28px;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
                border: none;
                width: 0px;
            }

            /* Progress Bar */
            QProgressBar {
                border: none;
                border-radius: 6px;
                text-align: center;
                background-color: rgba(255, 255, 255, 0.05);
                height: 8px;
                font-size: 1px;
                color: transparent;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #76e648, stop:1 #5da13a);
                border-radius: 6px;
            }

            /* Buttons */
            QPushButton {
                font-size: 13px;
                padding: 8px 16px;
                border-radius: 8px;
                min-height: 38px;
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            QPushButton#startBtn {
                background-color: rgba(118, 230, 72, 0.1);
                border: 1px solid rgba(118, 230, 72, 0.3);
                color: #76e648;
            }
            QPushButton#startBtn:hover {
                background-color: rgba(118, 230, 72, 0.2);
            }

            QPushButton#cancelBtn {
                background-color: rgba(255, 71, 87, 0.1);
                border: 1px solid rgba(255, 71, 87, 0.3);
                color: #ff4757;
            }

            QPushButton#pauseBtn {
                background-color: rgba(255, 165, 2, 0.1);
                border: 1px solid rgba(255, 165, 2, 0.3);
                color: #ffa502;
            }

            QStatusBar {
                background-color: transparent;
                color: #666666;
                font-size: 11px;
            }
        """
        )

        self.scraper = FourChanScraper()
        # Set default download directory to ~/Downloads/4Charm
        # NOTE: Do not create the folder until a download starts.
        default_dir = Path.home() / "Downloads" / "4Charm"
        self.scraper.download_dir = default_dir

        self.download_thread: QThread | None = None
        self.download_worker: MultiUrlDownloadWorker | None = None
        self.is_paused = False

        self.setup_ui()
        self.setup_connections()
        self._update_ui_for_state("idle")
        # Initialize download stats
        self.update_download_stats()
        # Show default download directory in status bar
        if self.scraper.download_dir:
            self.status_bar.showMessage(f"Download folder: {self.scraper.download_dir}")

    def setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        # Header Section
        header_container = QVBoxLayout()
        header_container.setSpacing(4)

        header = QLabel("4Charm")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            "font-size: 42px; font-weight: 800; color: #76e648; letter-spacing: -1px; margin-top: 10px;"
        )
        header_container.addWidget(header)

        slogan = QLabel("HIGH PERFORMANCE 4CHAN MEDIA DOWNLOADER")
        slogan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slogan.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #666666; letter-spacing: 2px; margin-bottom: 20px;"
        )
        header_container.addWidget(slogan)
        main_layout.addLayout(header_container)

        # URL Input Card
        url_master = QFrame()
        url_master.setObjectName("urlMasterContainer")
        # Removed fixed height to prevent overlap!
        url_master_layout = QVBoxLayout(url_master)
        url_master_layout.setContentsMargins(0, 0, 0, 0)
        url_master_layout.setSpacing(0)

        url_title = QLabel("  URLs TO DOWNLOAD")
        url_title.setObjectName("urlSectionTitle")
        url_master_layout.addWidget(url_title)

        # Editor Area
        editor_container = QFrame()
        editor_container.setObjectName("editorSurface")
        editor_layout = QHBoxLayout(editor_container)
        editor_layout.setContentsMargins(12, 8, 8, 8)
        editor_layout.setSpacing(8)

        # Line numbers
        self.line_numbers = QPlainTextEdit()
        self.line_numbers.setObjectName("lineNumberGutter")
        self.line_numbers.setReadOnly(True)
        self.line_numbers.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.line_numbers.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        self.line_numbers.setFrameStyle(QFrame.Shape.NoFrame)
        self.line_numbers.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.line_numbers.setFixedWidth(42)
        self.line_numbers.setMinimumHeight(280)
        self.line_numbers.document().setDocumentMargin(0)
        self.line_numbers.setPlainText("1")

        fmt = QTextBlockFormat()
        fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fmt.setLineHeight(
            140.0, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
        )
        cursor = self.line_numbers.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(fmt)

        editor_layout.addWidget(self.line_numbers)

        # URL input
        self.url_input = UrlInputEdit()
        self.url_input.setObjectName("urlInput")
        self.url_input.setFrameStyle(QFrame.Shape.NoFrame)
        self.url_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.url_input.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.url_input.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.url_input.setPlaceholderText("Paste thread URLs here...")
        self.url_input.setMinimumHeight(280)
        self.url_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.url_input.document().setDocumentMargin(2)

        # Match line height with line_numbers
        cursor = self.url_input.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(fmt)

        editor_layout.addWidget(self.url_input)
        url_master_layout.addWidget(editor_container)

        # Action Buttons
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(15, 0, 15, 15)
        buttons_layout.setSpacing(12)

        self.folder_btn = QPushButton("📁 Folder")
        self.start_cancel_btn = QPushButton("🚀 Start")
        self.start_cancel_btn.setObjectName("startBtn")
        self.clear_btn = QPushButton("Clear")
        self.pause_resume_btn = QPushButton("⏸️ Pause")
        self.pause_resume_btn.setObjectName("pauseBtn")

        buttons_layout.addWidget(self.start_cancel_btn)
        buttons_layout.addWidget(self.clear_btn)
        buttons_layout.addWidget(self.folder_btn)
        buttons_layout.addWidget(self.pause_resume_btn)
        url_master_layout.addWidget(buttons_container)

        # Meta Info
        meta_layout = QHBoxLayout()
        meta_layout.setContentsMargins(15, 0, 15, 12)
        self.url_count_label = QLabel("QUEUE: 0")
        self.url_count_label.setStyleSheet(
            "color: #666666; font-size: 10px; font-weight: 800;"
        )
        meta_layout.addWidget(self.url_count_label)
        meta_layout.addStretch()
        url_master_layout.addLayout(meta_layout)

        main_layout.addWidget(url_master)

        # Progress Section
        progress_group = QGroupBox("DOWNLOAD PROGRESS")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(15, 20, 15, 15)
        progress_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        progress_info = QHBoxLayout()
        self.progress_label = QLabel("Ready to download...")
        self.progress_label.setStyleSheet("font-size: 12px; color: #888888;")
        self.speed_label = QLabel("0.0 MB/s")
        self.speed_label.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #76e648;"
        )
        progress_info.addWidget(self.progress_label)
        progress_info.addStretch()
        progress_info.addWidget(self.speed_label)
        progress_layout.addLayout(progress_info)
        main_layout.addWidget(progress_group)

        # Activity Log
        log_group = QGroupBox("ACTIVITY LOG")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(15, 20, 15, 15)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logView")
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(120)
        log_layout.addWidget(self.log_text)

        # Stats Section
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 5, 0, 0)
        self.folders_label = QLabel("FOLDERS: 0")
        self.files_label = QLabel("FILES: 0")
        self.size_label = QLabel("STORAGE: 0 MB")
        for lbl in [self.folders_label, self.files_label, self.size_label]:
            lbl.setStyleSheet("font-size: 10px; font-weight: 800; color: #555555;")
            stats_layout.addWidget(lbl)
            if lbl != self.size_label:
                stats_layout.addSpacing(15)
        stats_layout.addStretch()
        log_layout.addLayout(stats_layout)
        main_layout.addWidget(log_group)

        main_layout.addStretch()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Engine Status: Ready")

    def setup_connections(self):
        """Connect signals and slots."""
        self.url_input.textChanged.connect(self.validate_urls)

        # Sync scrolling: Input Box -> controls -> Line Numbers
        self.url_input.verticalScrollBar().valueChanged.connect(
            self.line_numbers.verticalScrollBar().setValue
        )
        self.url_input.verticalScrollBar().rangeChanged.connect(
            lambda min_val, max_val: self.line_numbers.verticalScrollBar().setValue(
                self.url_input.verticalScrollBar().value()
            )
        )
        self.url_input.cursorPositionChanged.connect(self._schedule_url_cursor_follow)
        self.start_cancel_btn.clicked.connect(self.handle_start_cancel_click)
        self.pause_resume_btn.clicked.connect(self.toggle_pause_resume)
        self.clear_btn.clicked.connect(self.clear_urls)
        self.folder_btn.clicked.connect(self.choose_download_folder)

        self.paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self.paste_shortcut.activated.connect(self.paste_from_clipboard)
        # Note: Enter key is NOT captured - it allows normal text editing (new lines/scrolling)
        # Validation happens automatically via textChanged signal
        self.download_shortcut = QShortcut(
            QKeySequence("Ctrl+Return"),
            self.url_input,
        )
        self.download_shortcut.activated.connect(
            self.handle_start_cancel_click
        )  # Ctrl+Enter to start download
        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.escape_shortcut.activated.connect(self.cancel_or_close)

    def clear_urls(self):
        """Clear all URLs from the input field."""
        self.url_input.clear()
        self.validate_urls()

    def choose_download_folder(self):
        """Open folder chooser dialog to select download location."""
        download_dir = self.scraper.download_dir
        if download_dir is None:
            fallback_dir = Path.home() / "Downloads"
            current_dir = str(fallback_dir if fallback_dir.exists() else Path.home())
        elif download_dir.exists():
            current_dir = str(download_dir)
        else:
            parent_dir = download_dir.parent
            current_dir = str(parent_dir if parent_dir.exists() else Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Download Folder", current_dir, QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            selected_dir = Path(folder)
            selected_dir.mkdir(parents=True, exist_ok=True)
            self.scraper.download_dir = selected_dir
            self.add_log_message(f"📁 Download folder changed to: {folder}")
            self.status_bar.showMessage(f"Download folder: {folder}")

    def _sync_scroll_bars(self):
        """Force scroll synchronization between input and line numbers."""
        current_scroll = self.url_input.verticalScrollBar().value()
        self.line_numbers.verticalScrollBar().setValue(current_scroll)

    def _keep_url_cursor_visible(self):
        """Keep the URL editor scrolled to the active cursor after layout updates."""
        self.url_input.ensureCursorVisible()
        self._sync_scroll_bars()

    def _schedule_url_cursor_follow(self):
        QTimer.singleShot(0, self._keep_url_cursor_visible)

    def validate_urls(self):
        """Validate URLs in real-time and update line numbers."""
        if getattr(self, "_validating", False):
            return

        # --- THE THREE-STEP PROCESS ---

        # 1. Counting the Lines
        # Use document().blockCount() - it's the most reliable way to track lines in real-time
        line_count = max(1, self.url_input.document().blockCount())

        # 2. Generating the Number Sequence
        # Create a sequence like "1\n2\n3\n4\n5\n6\n7"
        line_nums = "\n".join(str(i) for i in range(1, line_count + 1))

        if self.line_numbers.toPlainText() != line_nums:
            # Update the line numbers display
            self.line_numbers.setPlainText(line_nums)
            # Maintain perfect pixel alignment
            cursor = self.line_numbers.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            fmt = QTextBlockFormat()
            fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fmt.setLineHeight(
                140.0, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
            )
            cursor.setBlockFormat(fmt)
            # Clear selection to prevent highlighting
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.line_numbers.setTextCursor(cursor)

        # 3. Keeping Everything Synchronized
        # Defer cursor-follow until the editor has processed line and scroll range changes.
        self._schedule_url_cursor_follow()

        # --- END OF SYNC LOGIC ---

        raw_text = self.url_input.toPlainText()
        all_lines = raw_text.split("\n")
        raw_lines = [ln.strip() for ln in all_lines if ln.strip()]

        # Update the URL counter label
        self.url_count_label.setText(f"QUEUE: {len(raw_lines)}")

        # Validate URL count (maximum 20)
        if len(raw_lines) > 20:
            self._update_url_status(
                "⚠️ Maximum 20 URLs allowed. Please remove some URLs.", "invalid"
            )
            self.start_cancel_btn.setEnabled(False)
            return

        if not raw_lines:
            self.start_cancel_btn.setEnabled(False)
            return

        # Simple string check for speed (avoid creating Scraper object repeatedly in UI thread)
        valid_count = 0
        invalid_count = 0

        for url in raw_lines:
            # Basic check for 4chan domains
            if "boards.4chan.org" in url or "4channel.org" in url or "4chan.org" in url:
                valid_count += 1
            else:
                invalid_count += 1

        if valid_count > 0 and invalid_count == 0:
            self.start_cancel_btn.setEnabled(True)
            self._update_url_status(f"Ready to download {valid_count} threads", "valid")
        elif invalid_count > 0:
            self.start_cancel_btn.setEnabled(False)
            self._update_url_status("⚠️ Invalid 4chan URLs detected", "invalid")

    def handle_start_cancel_click(self):
        """Handles clicks on the main button, either starting or cancelling."""
        if self.download_thread and self.download_thread.isRunning():
            self.cancel_download()
        else:
            self.start_download()

    def start_download(self):
        """Start the download process for multiple URLs."""
        if not self.start_cancel_btn.isEnabled():
            return

        text = self.url_input.toPlainText().strip()
        urls = [url.strip() for url in text.split("\n") if url.strip()]
        if not urls:
            QMessageBox.critical(self, "Error", "No URLs provided")
            return

        # Check if download folder is set, if not prompt user
        if self.scraper.download_dir is None:
            folder = QFileDialog.getExistingDirectory(
                self,
                "Choose Download Folder",
                str(Path.home()),
                QFileDialog.Option.ShowDirsOnly,
            )

            if not folder:
                self.add_log_message("❌ Download cancelled - no folder selected")
                return

            selected_dir = Path(folder)
            selected_dir.mkdir(parents=True, exist_ok=True)
            self.scraper.download_dir = selected_dir
            self.add_log_message(f"📁 Download folder set to: {folder}")
            self.status_bar.showMessage(f"Download folder: {folder}")

        # Parse and validate URLs (strip numbering if present)
        parsed_urls = []
        for url in urls:
            # Strip numbering like "1. " from the beginning
            clean_url = re.sub(r"^\d+\.\s*", "", url.strip())
            parsed = self.scraper.parse_url(clean_url)
            if parsed:
                parsed_urls.append(parsed)
            else:
                self.add_log_message(f"⚠️ Skipping invalid URL: {clean_url}")

        if not parsed_urls:
            QMessageBox.critical(self, "Error", "No valid URLs found")
            return

        download_dir = self.scraper.download_dir
        if download_dir is None:
            self.add_log_message("❌ Download cancelled - no folder selected")
            return

        # Ensure download directory exists before starting
        download_dir.mkdir(parents=True, exist_ok=True)

        self.download_thread = QThread()
        self.download_worker = MultiUrlDownloadWorker(self.scraper, parsed_urls)
        self.download_worker.moveToThread(self.download_thread)

        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.speed_update.connect(self.update_speed)
        self.download_worker.log_message.connect(self.add_log_message)
        self.download_worker.finished.connect(self.download_finished)
        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_thread.finished.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        self.download_thread.finished.connect(self.thread_cleanup)

        self.log_text.clear()
        self._update_ui_for_state("downloading")
        self.status_bar.showMessage(f"Downloading from {len(parsed_urls)} URLs...")
        self.download_thread.start()

    def cancel_download(self):
        """Cancel the current download."""
        if self.download_worker:
            self.download_worker.cancel()
            self.add_log_message("🛑 Cancelling download...")
            self.start_cancel_btn.setEnabled(False)

    def download_finished(self, stats: dict):
        """Handle download completion. This should ONLY update the UI."""
        self._update_ui_for_state("idle")

        total, downloaded, size_mb, duplicates = (
            stats.get("total", 0),
            stats.get("downloaded", 0),
            stats.get("size_mb", 0),
            stats.get("duplicates", 0),
        )
        status_msg = f"Complete: {downloaded}/{total} files ({size_mb:.1f}MB)"
        if duplicates > 0:
            status_msg += f" | {duplicates} duplicates skipped"
        self.status_bar.showMessage(status_msg if total > 0 else "No files found")

    def thread_cleanup(self):
        """Safely nullify thread and worker references after the thread has finished."""
        logger.info("QThread has finished, cleaning up references.")
        self.download_thread = None
        self.download_worker = None

    def toggle_pause_resume(self):
        """Toggle pause/resume state."""
        if self.download_worker:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.download_worker.pause()
                self.add_log_message("⏸️ Downloads paused")
                self._update_ui_for_state("paused")
            else:
                self.download_worker.resume()
                self.add_log_message("▶️ Downloads resumed")
                self._update_ui_for_state("downloading")

    def _update_ui_for_state(self, state: str):
        """Update the entire UI based on the application state."""
        if state == "idle":
            self.start_cancel_btn.setText("🚀 Start Download")
            self.start_cancel_btn.setObjectName("startBtn")
            self.pause_resume_btn.setVisible(False)
            self.validate_urls()
            self.speed_label.setText("0.0 MB/s")
        elif state == "downloading":
            self.start_cancel_btn.setText("🛑 Cancel")
            self.start_cancel_btn.setObjectName("cancelBtn")
            self.start_cancel_btn.setEnabled(True)
            self.pause_resume_btn.setText("⏸️ Pause")
            self.pause_resume_btn.setVisible(True)
            self.is_paused = False
        elif state == "paused":
            self.pause_resume_btn.setText("▶️ Resume")

        self.start_cancel_btn.style().unpolish(self.start_cancel_btn)
        self.start_cancel_btn.style().polish(self.start_cancel_btn)

    def _update_url_status(self, text: str, state: str):
        """Update the URL status label with appropriate text and color."""
        colors = {
            "valid": "#76e648",
            "invalid": "#f44336",
            "partial": "#FF9800",
            "idle": "#666666",
        }
        color = colors.get(state, "#666666")
        self.status_bar.showMessage(text)
        self.status_bar.setStyleSheet(
            f"QStatusBar {{ color: {color}; font-size: 11px; font-weight: 800; padding: 4px; letter-spacing: 0.5px; }}"
        )

    def update_progress(
        self,
        current: int,
        total: int,
        filename: str,
        speed: float,
        thread_name: str = "",
        thread_index: int = 0,
        eta: float = 0.0,
    ):
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))

            # Format ETA if available
            eta_str = ""
            if eta > 0:
                if eta < 60:
                    eta_str = f" - ETA: {int(eta)}s"
                elif eta < 3600:
                    eta_str = f" - ETA: {int(eta / 60)}m {int(eta % 60)}s"
                else:
                    hours = int(eta / 3600)
                    minutes = int((eta % 3600) / 60)
                    eta_str = f" - ETA: {hours}h {minutes}m"

            if thread_name and thread_index > 0:
                self.progress_label.setText(
                    f"Progress: {current}/{total} files - [{thread_index}] {thread_name} - {filename}{eta_str}"
                )
            else:
                self.progress_label.setText(
                    f"Progress: {current}/{total} files - {filename}{eta_str}"
                )

    def update_speed(self, speed: float):
        self.speed_label.setText(f"{speed:.1f} MB/s")

    def add_log_message(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        # Update stats after each log message
        self.update_download_stats()

    def update_download_stats(self):
        """Update folder, file, and size statistics using macOS du command."""
        try:
            if (
                self.scraper.download_dir is None
                or not self.scraper.download_dir.exists()
            ):
                self.folders_label.setText("Folders: 0")
                self.files_label.setText("Files: 0")
                self.size_label.setText("Size: 0 MB")
                return

            # Count folders (subdirectories only, not the root)
            folders = [d for d in self.scraper.download_dir.iterdir() if d.is_dir()]
            folder_count = len(folders)

            # Count files recursively
            file_count = sum(
                1 for _ in self.scraper.download_dir.rglob("*") if _.is_file()
            )

            # Get size using macOS du command (more accurate)
            try:
                result = subprocess.run(
                    ["du", "-sk", str(self.scraper.download_dir)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    size_kb = int(result.stdout.split()[0])
                    size_mb = size_kb / 1024
                else:
                    # Fallback to Python calculation
                    size_mb = sum(
                        f.stat().st_size
                        for f in self.scraper.download_dir.rglob("*")
                        if f.is_file()
                    ) / (1024 * 1024)
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
                # Fallback to Python calculation
                size_mb = sum(
                    f.stat().st_size
                    for f in self.scraper.download_dir.rglob("*")
                    if f.is_file()
                ) / (1024 * 1024)

            # Update labels
            self.folders_label.setText(f"FOLDERS: {folder_count}")
            self.files_label.setText(f"FILES: {file_count}")
            self.size_label.setText(f"STORAGE: {size_mb:.1f} MB")

        except Exception as e:
            logger.warning(f"Could not update download stats: {e}")

    def paste_from_clipboard(self):
        """Paste URLs from clipboard with auto-formatting."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()

        if not text:
            return

        valid_urls = _extract_supported_urls(text)

        if valid_urls:
            _insert_url_lines(self.url_input, valid_urls)
        else:
            # Fallback: Normal paste if no valid URLs found
            self.url_input.paste()

        # Ensure everything is visible and validated
        self._schedule_url_cursor_follow()
        self.validate_urls()

    def cancel_or_close(self):
        if self.download_thread and self.download_thread.isRunning():
            self.cancel_download()
        else:
            self.close()

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure complete cleanup when window is closed."""
        logger.info("MainWindow closing - performing complete cleanup")

        # Cancel any active downloads
        if self.download_thread and self.download_thread.isRunning():
            logger.info("Cancelling active downloads")
            self.cancel_download()

        # Wait for thread to finish (with timeout)
        if self.download_thread:
            logger.info("Waiting for download thread to finish")
            self.download_thread.quit()
            if not self.download_thread.wait(3000):  # 3 second timeout
                logger.warning("Thread did not finish gracefully, terminating")
                self.download_thread.terminate()
                self.download_thread.wait(1000)  # Final wait for termination

        # Force garbage collection
        import gc

        gc.collect()

        # Accept the close event
        event.accept()
        logger.info("MainWindow cleanup complete")

    @override
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    @override
    def dropEvent(self, event: QDropEvent) -> None:
        text = event.mimeData().text().strip()
        valid_urls = _extract_supported_urls(text)
        if valid_urls:
            _insert_url_lines(self.url_input, valid_urls)
            self.validate_urls()
            self._schedule_url_cursor_follow()


if __name__ == "__main__":
    # Setup basic logging for standalone run
    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
