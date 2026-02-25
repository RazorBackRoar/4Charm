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
from urllib.parse import urlparse

try:
    from typing import override
except ImportError:  # pragma: no cover - Python < 3.12 build compatibility
    def override(func):
        return func

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import (
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
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from four_charm.core.scraper import FourChanScraper
from four_charm.gui.workers import MultiUrlDownloadWorker


logger = logging.getLogger("4Charm")


def _is_4chan_host(url: str) -> bool:
    """Return True when the URL host matches an allowed 4chan domain."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    host = (parsed.netloc or "").split(":", 1)[0].lower()
    if host.startswith("www."):
        host = host[4:]
    return host in {"boards.4chan.org", "4chan.org", "4channel.org"}


def _extract_valid_4chan_urls(raw_text: str) -> list[str]:
    """Extract valid 4chan URLs from text while preserving source order."""
    if not raw_text:
        return []
    urls = re.findall(r"https?://[^\s]+", raw_text)
    return [url for url in urls if _is_4chan_host(url)]


def _append_urls_to_input(existing_text: str, incoming_text: str) -> str:
    """Append valid URLs from incoming text without clearing existing entries."""
    valid_urls = _extract_valid_4chan_urls(incoming_text)
    if not valid_urls:
        return existing_text

    existing = existing_text.rstrip("\n")
    incoming = "\n".join(valid_urls)
    if not existing:
        return incoming
    return f"{existing}\n{incoming}"


def _format_clipboard_paste_text(
    raw_text: str,
    position_in_block: int,
    current_block_text: str = "",
) -> str:
    """Normalize pasted text for URL input and always end on a new line."""
    if not raw_text:
        return ""

    valid_urls = _extract_valid_4chan_urls(raw_text)
    paste_text = "\n".join(valid_urls) if valid_urls else raw_text

    should_prefix_newline = position_in_block > 0 or (
        position_in_block == 0 and bool(current_block_text.strip())
    )
    if should_prefix_newline and not paste_text.startswith("\n"):
        paste_text = "\n" + paste_text
    if not paste_text.endswith("\n"):
        paste_text += "\n"
    return paste_text


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("")
        self.setMinimumSize(850, 730)
        self.resize(850, 730)
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
                border-radius: 12px;
                background-color: rgba(30, 30, 30, 0.4);
                margin-top: 10px;
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

            QTextEdit#logView {
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 6px;
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
        editor_container = QWidget()
        editor_layout = QHBoxLayout(editor_container)
        editor_layout.setContentsMargins(15, 0, 15, 10)
        editor_layout.setSpacing(10)

        # Line numbers
        self.line_numbers = QPlainTextEdit()
        self.line_numbers.setReadOnly(True)
        self.line_numbers.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.line_numbers.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        self.line_numbers.setFrameStyle(QFrame.Shape.NoFrame)
        self.line_numbers.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.line_numbers.setFixedWidth(40)
        self.line_numbers.document().setDocumentMargin(0)
        self.line_numbers.setStyleSheet(
            "color: rgba(118, 230, 72, 0.5); "
            "padding: 12px 0px; "
            "selection-background-color: transparent; "
            "selection-color: rgba(118, 230, 72, 0.5);"
        )
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
        self.url_input = QPlainTextEdit()
        self.url_input.setFrameStyle(QFrame.Shape.NoFrame)
        self.url_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.url_input.setPlaceholderText("Paste thread URLs here...")
        self.url_input.setFixedHeight(120)
        self.url_input.document().setDocumentMargin(0)
        self.url_input.setStyleSheet("padding: 12px 0px;")

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
        # Ensure the cursor is always visible (especially when adding lines)
        self.url_input.ensureCursorVisible()

        # We use a 0ms timer to defer scroll sync until the widget has processed the text update.
        # This prevents the scrollbar from being 'capped' at the old maximum range when adding lines.
        QTimer.singleShot(0, self._sync_scroll_bars)

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

        # Use the same hostname validation logic as paste/drop handlers.
        valid_count = 0
        invalid_count = 0

        for url in raw_lines:
            if _is_4chan_host(url):
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
    ):
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
            if thread_name and thread_index > 0:
                self.progress_label.setText(
                    f"Progress: {current}/{total} files - [{thread_index}] {thread_name} - {filename}"
                )
            else:
                self.progress_label.setText(
                    f"Progress: {current}/{total} files - {filename}"
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

        cursor = self.url_input.textCursor()
        paste_text = _format_clipboard_paste_text(
            text,
            cursor.positionInBlock(),
            cursor.block().text(),
        )
        if not paste_text:
            return

        cursor.insertText(paste_text)
        self.url_input.setTextCursor(cursor)

        # Ensure everything is visible and validated
        self.url_input.ensureCursorVisible()
        self.validate_urls()

        # Scroll to bottom to show new entries
        scrollbar = self.url_input.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def cancel_or_close(self):
        if self.download_thread and self.download_thread.isRunning():
            self.cancel_download()
        else:
            self.close()

    @override
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    @override
    def dropEvent(self, event: QDropEvent) -> None:
        existing_text = self.url_input.toPlainText()
        merged_text = _append_urls_to_input(existing_text, event.mimeData().text())
        if merged_text != existing_text:
            self.url_input.setPlainText(merged_text)
            cursor = self.url_input.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.url_input.setTextCursor(cursor)
            self.url_input.ensureCursorVisible()
            self.validate_urls()
            event.acceptProposedAction()


if __name__ == "__main__":
    # Setup basic logging for standalone run
    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
