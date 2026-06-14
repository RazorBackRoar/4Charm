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
import sys
from datetime import datetime
from pathlib import Path
from typing import override

from PySide6.QtCore import QSize, Qt, QThread, QTimer
from PySide6.QtGui import (
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
    QShortcut,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from four_charm.core.scraper import FourChanScraper
from four_charm.gui.widgets import (
    ActivityLog,
    LineNumberTextEdit,
    NeonButton,
    NeonPanel,
    StatCard,
    create_interface_icon,
)
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


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("4Charm")
        self.setMinimumSize(1080, 780)
        self.resize(1280, 860)
        self.setAcceptDrops(True)

        self.scraper = FourChanScraper()
        default_dir = Path.home() / "Downloads" / "4Charm"
        self.scraper.download_dir = default_dir

        self.download_thread: QThread | None = None
        self.download_worker: MultiUrlDownloadWorker | None = None
        self.is_paused = False
        self.session_folders: set[str] = set()

        self._load_styles()
        self._build_ui()
        self.setup_connections()
        self._update_ui_for_state("idle")
        self.update_download_stats()
        self._populate_initial_log()

    def _load_styles(self) -> None:
        import sys
        if getattr(sys, "frozen", False):
            # _MEIPASS only exists in PyInstaller-frozen builds (guarded above)
            base_path = Path(sys._MEIPASS)  # ty: ignore[unresolved-attribute]
            qss_path = base_path / "four_charm" / "gui" / "style.qss"
        else:
            qss_path = Path(__file__).parent / "style.qss"

        if qss_path.exists():
            logger.info(f"Loading stylesheet from: {qss_path}")
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        else:
            fallback_path = Path(__file__).parent / "style.qss"
            if fallback_path.exists():
                logger.info(f"Loading stylesheet from fallback: {fallback_path}")
                self.setStyleSheet(fallback_path.read_text(encoding="utf-8"))
            else:
                logger.error(f"CRITICAL: style.qss not found! Looked in {qss_path} and {fallback_path}")

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(32, 18, 32, 16)
        main_layout.setSpacing(14)

        header = self._build_header()
        url_panel = self._build_url_panel()
        progress_panel = self._build_progress_panel()
        lower_area = self._build_lower_area()

        main_layout.addWidget(header)
        main_layout.addWidget(url_panel)
        main_layout.addWidget(progress_panel)
        main_layout.addWidget(lower_area, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setProperty("statusState", "idle")
        self.status_indicator = QLabel()
        self.status_indicator.setObjectName("StatusIndicator")
        self.status_indicator.setFixedSize(10, 10)
        self.status_message = QLabel("Engine Status: Ready")
        self.status_message.setObjectName("StatusMessage")
        self.status_bar.addWidget(self.status_indicator)
        self.status_bar.addWidget(self.status_message, 1)
        self.status_bar.setSizeGripEnabled(False)

    def _build_header(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("Header")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 10)
        layout.setSpacing(4)
        title = QLabel("4Charm")
        title.setObjectName("AppTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("HIGH PERFORMANCE 4CHAN MEDIA DOWNLOADER")
        subtitle.setObjectName("AppSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return panel

    def _build_section_label(self, text: str) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("SectionHeader")
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        accent = QFrame()
        accent.setObjectName("SectionAccent")
        accent.setFixedSize(4, 22)

        label = QLabel(text)
        label.setObjectName("SectionLabel")

        layout.addWidget(accent)
        layout.addWidget(label)
        layout.addStretch()
        return wrapper

    def _build_url_panel(self) -> NeonPanel:
        panel = NeonPanel("UrlPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(9)
        label = self._build_section_label("URLS TO DOWNLOAD")

        self.url_input_frame = LineNumberTextEdit(panel)
        self.url_input_frame.setMinimumHeight(190)
        self.url_input_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.url_input = self.url_input_frame.editor
        self.line_numbers = self.url_input_frame.line_numbers

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.start_cancel_btn = NeonButton("Start Download")
        self.start_cancel_btn.setObjectName("startBtn")
        self.clear_btn = NeonButton("Clear")
        self.folder_btn = NeonButton("Folder")
        self.pause_resume_btn = NeonButton("Pause")
        self.pause_resume_btn.setObjectName("pauseBtn")

        icon_size = QSize(22, 22)
        self.start_cancel_btn.setIcon(create_interface_icon("play"))
        self.start_cancel_btn.setIconSize(icon_size)
        self.clear_btn.setIcon(create_interface_icon("trash"))
        self.clear_btn.setIconSize(icon_size)
        self.folder_btn.setIcon(create_interface_icon("folder"))
        self.folder_btn.setIconSize(icon_size)
        self.pause_resume_btn.setIcon(create_interface_icon("pause"))
        self.pause_resume_btn.setIconSize(icon_size)

        button_row.addWidget(self.start_cancel_btn)
        button_row.addWidget(self.pause_resume_btn)
        button_row.addWidget(self.clear_btn)
        button_row.addWidget(self.folder_btn)

        self.url_count_label = QLabel("QUEUE: 0")
        self.url_count_label.setObjectName("QueueLabel")

        layout.addWidget(label)
        layout.addWidget(self.url_input_frame, stretch=1)
        layout.addLayout(button_row)
        layout.addWidget(self.url_count_label)
        return panel

    def _build_progress_panel(self) -> NeonPanel:
        panel = NeonPanel("ProgressPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 11, 14, 12)
        layout.setSpacing(7)
        label = self._build_section_label("DOWNLOAD PROGRESS")

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("DownloadProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        status_row = QHBoxLayout()
        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("StatusLabel")
        self.speed_label = QLabel("0.0 MB/s")
        self.speed_label.setObjectName("SpeedLabel")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        status_row.addWidget(self.progress_label)
        status_row.addStretch()
        status_row.addWidget(self.speed_label)

        layout.addWidget(label)
        layout.addLayout(status_row)
        layout.addWidget(self.progress_bar)
        return panel

    def _build_lower_area(self) -> QWidget:
        wrapper = QWidget()
        self.lower_layout = QHBoxLayout(wrapper)
        self.lower_layout.setContentsMargins(0, 0, 0, 0)
        self.lower_layout.setSpacing(12)

        self.log_panel = NeonPanel("LogPanel")
        log_layout = QVBoxLayout(self.log_panel)
        log_layout.setContentsMargins(14, 12, 14, 14)
        log_layout.setSpacing(8)
        label = self._build_section_label("ACTIVITY LOG")
        self.log_text = ActivityLog()
        self.log_text.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        log_layout.addWidget(label)
        log_layout.addWidget(self.log_text)

        self.stats_panel = QWidget()
        self.stats_panel.setObjectName("StatsPanel")
        self.stats_panel.setFixedWidth(290)
        self.stats_layout = QVBoxLayout(self.stats_panel)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_layout.setSpacing(10)

        self.folders_card = StatCard(
            "FOLDERS",
            "0",
            create_interface_icon("folder", size=30),
        )
        self.files_card = StatCard(
            "FILES",
            "0",
            create_interface_icon("file", size=30),
        )
        self.storage_card = StatCard(
            "STORAGE",
            "0.0GB",
            create_interface_icon("drive", size=30),
        )

        self.stats_layout.addWidget(self.folders_card)
        self.stats_layout.addWidget(self.files_card)
        self.stats_layout.addWidget(self.storage_card)
        self.stats_layout.addStretch()

        self.lower_layout.addWidget(self.log_panel, stretch=1)
        self.lower_layout.addWidget(self.stats_panel)
        return wrapper

    def _populate_initial_log(self) -> None:
        """Show a concise startup summary without changing application state."""
        for message in (
            "Engine initialized",
            "Ready to download...",
            "Waiting for URLs...",
            "System check complete",
            "All systems operational",
            "Queue is empty",
        ):
            self.add_log_message(message)

    def setup_connections(self):
        """Connect signals and slots."""
        self.url_input_frame.editor.textChanged.connect(self.validate_urls)

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
        """Clear all URLs and reset UI state."""
        self.url_input.clear()
        self.validate_urls()

        # Reset progress
        self.progress_bar.setValue(0)
        self.progress_label.setText("Ready")
        self.speed_label.setText("0.0 MB/s")

        # Clear log
        self.log_text.clear()

        # Reset session counters
        self.session_folders.clear()
        self.folders_card.set_value("0")
        self.files_card.set_value("0")
        self.storage_card.set_value("0.0GB")

        # Reset scraper stats
        self.scraper.stats["downloaded"] = 0
        self.scraper.stats["size_mb"] = 0.0
        self._update_url_status("Engine Status: Ready", "idle")

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
            self.add_log_message(f"Download folder changed to: {folder}")
            self._set_status_message(f"Download folder: {folder}")

    def _sync_scroll_bars(self):
        """Force scroll synchronization between input and line numbers."""
        current_scroll = self.url_input.verticalScrollBar().value()
        self.line_numbers.verticalScrollBar().setValue(current_scroll)

    def validate_urls(self):
        """Validate URLs in real-time and update line numbers."""
        raw_text = self.url_input.toPlainText()
        all_lines = raw_text.split("\n")
        raw_lines = [ln.strip() for ln in all_lines if ln.strip()]

        # Update the URL counter label
        self.url_count_label.setText(f"QUEUE: {len(self.url_input_frame.urls())}")

        # Validate URL count (maximum 20)
        if len(raw_lines) > 20:
            self._update_url_status(
                "Maximum 20 URLs allowed. Please remove some URLs.", "invalid"
            )
            self.start_cancel_btn.setEnabled(False)
            return

        if not raw_lines:
            self.start_cancel_btn.setEnabled(False)
            self._update_url_status("Engine Status: Ready", "idle")
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
            self._update_url_status("Invalid 4chan URLs detected", "invalid")

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
                self.add_log_message("Download cancelled - no folder selected")
                return

            selected_dir = Path(folder)
            selected_dir.mkdir(parents=True, exist_ok=True)
            self.scraper.download_dir = selected_dir
            self.add_log_message(f"Download folder set to: {folder}")
            self._set_status_message(f"Download folder: {folder}")

        # Parse and validate URLs (strip numbering if present)
        parsed_urls = []
        for url in urls:
            # Strip numbering like "1. " from the beginning
            clean_url = re.sub(r"^\d+\.\s*", "", url.strip())
            parsed = self.scraper.parse_url(clean_url)
            if parsed:
                parsed_urls.append(parsed)
            else:
                self.add_log_message(f"Skipping invalid URL: {clean_url}")

        if not parsed_urls:
            QMessageBox.critical(self, "Error", "No valid URLs found")
            return

        download_dir = self.scraper.download_dir
        if download_dir is None:
            self.add_log_message("Download cancelled - no folder selected")
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
        self._set_status_message(
            f"Downloading from {len(parsed_urls)} URLs...", "valid"
        )
        self.download_thread.start()

    def cancel_download(self):
        """Cancel the current download."""
        if self.download_worker:
            self.download_worker.cancel()
            self.add_log_message("Cancelling download...")
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
        self.progress_label.setText("Complete" if total > 0 else "Ready")
        self.status_bar.setProperty(
            "statusState", "valid" if total > 0 else "idle"
        )
        self._set_status_message(
            status_msg if total > 0 else "No files found",
            "valid" if total > 0 else "idle",
        )

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
                self.add_log_message("Downloads paused")
                self._update_ui_for_state("paused")
            else:
                self.download_worker.resume()
                self.add_log_message("Downloads resumed")
                self._update_ui_for_state("downloading")

    def _update_ui_for_state(self, state: str):
        """Update the entire UI based on the application state."""
        if state == "idle":
            self.start_cancel_btn.setText("Start Download")
            self.start_cancel_btn.setObjectName("startBtn")
            self.start_cancel_btn.setIcon(create_interface_icon("play"))
            self.pause_resume_btn.setText("Pause")
            self.pause_resume_btn.setIcon(create_interface_icon("pause"))
            self.pause_resume_btn.setVisible(False)
            self.validate_urls()
            self.speed_label.setText("0.0 MB/s")
        elif state == "downloading":
            self.start_cancel_btn.setText("Cancel")
            self.start_cancel_btn.setObjectName("cancelBtn")
            self.start_cancel_btn.setIcon(create_interface_icon("cancel"))
            self.start_cancel_btn.setEnabled(True)
            self.pause_resume_btn.setText("Pause")
            self.pause_resume_btn.setIcon(create_interface_icon("pause"))
            self.pause_resume_btn.setVisible(True)
            self.is_paused = False
            if self.progress_bar.value() == 0:
                self.progress_label.setText("Downloading 0%")
        elif state == "paused":
            self.pause_resume_btn.setText("Resume")
            self.pause_resume_btn.setIcon(create_interface_icon("play"))

        self.start_cancel_btn.style().unpolish(self.start_cancel_btn)
        self.start_cancel_btn.style().polish(self.start_cancel_btn)

    def _update_url_status(self, text: str, state: str):
        """Update the URL status label with appropriate text and color."""
        self._set_status_message(text, state)

    def _set_status_message(self, text: str, state: str | None = None) -> None:
        """Update the visible status label while preserving QStatusBar integration."""
        if state is not None:
            self.status_bar.setProperty("statusState", state)
        self.status_message.setText(text)
        self.status_bar.style().unpolish(self.status_bar)
        self.status_bar.style().polish(self.status_bar)

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
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)

            # Update session counters
            self.files_card.set_value(str(current))
            if thread_name:
                self.session_folders.add(thread_name)
            self.folders_card.set_value(str(len(self.session_folders)))

            size_mb = self.scraper.stats.get("size_mb", 0.0)
            size_gb = size_mb / 1024.0
            self.storage_card.set_value(f"{size_gb:.1f}GB")

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
                    f"Downloading {percent}% - {current}/{total} files - "
                    f"[{thread_index}] {thread_name} - {filename}{eta_str}"
                )
            else:
                self.progress_label.setText(
                    f"Downloading {percent}% - {current}/{total} files - "
                    f"{filename}{eta_str}"
                )

    def update_speed(self, speed: float):
        self.speed_label.setText(f"{speed:.1f} MB/s")

    def add_log_message(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.add_line(f"[{timestamp}] {message}")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        # Update stats after each log message
        self.update_download_stats()

    def update_download_stats(self):
        """Update folder, file, and size statistics for the active session only."""
        try:
            folder_count = len(getattr(self, "session_folders", set()))
            self.folders_card.set_value(str(folder_count))

            file_count = self.scraper.stats.get("downloaded", 0)
            self.files_card.set_value(str(file_count))

            size_mb = self.scraper.stats.get("size_mb", 0.0)
            size_gb = size_mb / 1024.0
            self.storage_card.set_value(f"{size_gb:.1f}GB")
        except Exception as e:
            logger.warning(f"Could not update session download stats: {e}")

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
        self.validate_urls()
        self.url_input.ensureCursorVisible()

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


if __name__ == "__main__":
    # Setup basic logging for standalone run
    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
