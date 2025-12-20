import re
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import sys
import os

# Add src to path to allow direct execution
current_file = Path(__file__).resolve()
src_path = current_file.parents[2] # gui -> four_charm -> src
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QSizePolicy,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QTextEdit,
    QPushButton,
    QGroupBox,
    QFrame,
    QProgressBar,
    QMessageBox,
    QStatusBar,
    QSizePolicy,
    QFileDialog,
)
from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QTextCursor,
    QTextBlockFormat,
    QKeySequence,
    QShortcut,
)

from four_charm.core.scraper import FourChanScraper
from four_charm.gui.workers import MultiUrlDownloadWorker

logger = logging.getLogger("4Charm")


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
            QMainWindow { background-color: #1a1a1a; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
            QWidget#centralWidget { border-top: 2px solid #76e648; }
            QWidget#urlMasterContainer {
                border: 2px solid #76e648;
                border-radius: 6px;
                background-color: #1e1e1e;
                margin-top: 12px;
            }
            QLabel#urlSectionTitle {
                color: #76e648;
                font-size: 14px;
                font-weight: 600;
                padding: 4px 8px;
                background-color: transparent;
            }
            QPlainTextEdit {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 13px;
            }
            QLineEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #404040; border-radius: 10px; padding: 12px 16px; font-size: 16px; selection-background-color: #76e648; }
            QLineEdit:focus { border: 2px solid #76e648; background-color: #353535; }
            QTextEdit { background-color: #2d2d2d; color: #ffffff; border: 2px solid #76e648; border-radius: 0px; padding: 8px 12px; font-size: 16px; selection-background-color: #76e648; line-height: 1.4; }
            QTextEdit:focus { border: 2px solid #76e648; background-color: #353535; border-radius: 0px; }
            QLabel { color: #cccccc; font-size: 15px; }
            QPushButton { font-size: 15px; padding: 8px 16px; border-radius: 8px; border: none; min-height: 36px; font-weight: 600; }
            QPushButton:hover { background-color: #5a5a5a; }
            QPushButton:pressed { background-color: #4a4a4a; }
            QPushButton:disabled { background-color: #404040; color: #888888; }
            QPushButton#startBtn { font-size: 15px; color: #76e648; background-color: transparent; border: 2px solid #76e648; font-weight: 600; border-radius: 8px; }
            QPushButton#startBtn:hover { background-color: #1a3a0a; }
            QPushButton#startBtn:disabled { background-color: #404040; color: #888888; border: 2px solid #404040; }
            QPushButton#cancelBtn { font-size: 15px; background-color: #ff4757; color: white; border-radius: 8px; }
            QPushButton#cancelBtn:hover { background-color: #ff3838; }
            QPushButton#pauseBtn { background-color: #ffa502; color: #1a1a1a; font-weight: 700; border-radius: 8px; }
            QPushButton#pauseBtn:hover { background-color: #ff8c00; }
            QProgressBar { border: none; border-radius: 8px; text-align: center; background-color: #2d2d2d; min-height: 24px; font-size: 13px; font-weight: 600; color: #ffffff; }
            QProgressBar::chunk { background-color: #76e648; border-radius: 0px; }
            QFrame#sectionFrame { border: none; background-color: transparent; }
            QStatusBar { background-color: #242424; color: #888888; border-top: 1px solid #404040; padding: 8px; font-size: 13px; }
        """
        )

        self.scraper = FourChanScraper()
        # Set default download directory: ~/Downloads/4Charm
        default_dir = Path.home() / "Downloads" / "4Charm"
        default_dir.mkdir(parents=True, exist_ok=True)
        self.scraper.download_dir = default_dir

        self.download_thread: Optional[QThread] = None
        self.download_worker: Optional["MultiUrlDownloadWorker"] = None
        self.is_paused = False

        self.setup_ui()
        self.setup_connections()
        self._update_ui_for_state("idle")
        # Initialize download stats
        self.update_download_stats()

    def setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        header = QLabel("4Charm")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(
            "font-size: 34px; font-weight: 700; color: #76e648; margin: 15px 0 5px 0;"
        )
        main_layout.addWidget(header)

        slogan = QLabel("The Phenomenal 4chan Media Downloader for macOS")
        slogan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slogan.setStyleSheet(
            "font-size: 14px; font-weight: 500; color: #888888; margin-bottom: 15px; letter-spacing: 0.5px;"
        )
        main_layout.addWidget(slogan)

        instruction = QLabel(
            "Paste or drop multiple thread URLs (one per line) to download all media files concurrently\nURLs are validated automatically | Press Ctrl+Enter to start download"
        )
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction.setStyleSheet(
            "color: #888888; font-size: 15px; margin: 15px 0; line-height: 1.5;"
        )
        main_layout.addWidget(instruction)

        # Native Qt Master Container Pattern (Stable Fixed Height Version)
        url_master = QFrame()
        url_master.setObjectName("urlMasterContainer")
        url_master.setFixedHeight(240)
        url_master.setStyleSheet("#urlMasterContainer { border: 2px solid #76e648; border-radius: 6px; background-color: #242424; }")
        url_master_layout = QVBoxLayout(url_master)
        url_master_layout.setContentsMargins(0, 0, 0, 0)
        url_master_layout.setSpacing(0)

        # 1. Section Title (Inside Master)
        url_title = QLabel("  URLs to Download")
        url_title.setObjectName("urlSectionTitle")
        url_title.setStyleSheet("padding: 10px 12px; font-weight: 700;")
        url_master_layout.addWidget(url_title)

        # 2. Content Row (Numbers | Vertical Separator | Input)
        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Left side: Line numbers (QPlainTextEdit)
        self.line_numbers = QPlainTextEdit()
        self.line_numbers.setReadOnly(True)
        self.line_numbers.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.line_numbers.setFrameStyle(QFrame.Shape.NoFrame)
        self.line_numbers.setViewportMargins(0, 0, 0, 0)
        self.line_numbers.setBackgroundVisible(False)
        self.line_numbers.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.line_numbers.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.line_numbers.setFixedWidth(40)
        self.line_numbers.setStyleSheet("color: #76e648; padding-top: 10px;")
        self.line_numbers.setPlainText("1")
        self.line_numbers.document().setDocumentMargin(4)

        # Doc-wide centering for QPlainTextEdit
        fmt = QTextBlockFormat()
        fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cursor = self.line_numbers.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(fmt)

        content_layout.addWidget(self.line_numbers)

        # Vertical separator line
        v_sep = QFrame()
        v_sep.setFrameShape(QFrame.Shape.VLine)
        v_sep.setFixedWidth(2)
        v_sep.setStyleSheet("background-color: #76e648; border: none; margin: 0px;")
        content_layout.addWidget(v_sep)

        # Right side: URL input (QPlainTextEdit)
        self.url_input = QPlainTextEdit()
        self.url_input.setFrameStyle(QFrame.Shape.NoFrame)
        self.url_input.setViewportMargins(0, 0, 0, 0)
        self.url_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.url_input.setPlaceholderText("Enter thread URLs here, one per line...")
        self.url_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.url_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.url_input.setStyleSheet("color: #ffffff; padding: 10px 8px;")
        self.url_input.document().setDocumentMargin(4)

        # Kill implicit scrollbar width
        self.url_input.verticalScrollBar().setStyleSheet("width: 0px;")

        content_layout.addWidget(self.url_input)
        url_master_layout.addWidget(content_container)

        # 3. Middle Horizontal Separator (Above Buttons)
        mid_sep = QFrame()
        mid_sep.setFrameShape(QFrame.Shape.HLine)
        mid_sep.setFixedHeight(2)
        mid_sep.setStyleSheet("background-color: #76e648; border: none;")
        url_master_layout.addWidget(mid_sep)

        # 4. Control Buttons (Inside Master)
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(15, 12, 15, 12)
        buttons_layout.setSpacing(15)

        self.folder_btn = QPushButton("📁 Choose Folder")
        self.folder_btn.setMinimumWidth(150)
        self.folder_btn.setStyleSheet(
            "QPushButton { color: #76e648; background-color: transparent; border: 2px solid #76e648; font-size: 15px; font-weight: 600; padding: 8px 16px; border-radius: 8px; } "
            "QPushButton:hover { background-color: rgba(118, 230, 72, 0.1); }"
        )
        buttons_layout.addWidget(self.folder_btn)

        self.start_cancel_btn = QPushButton("🚀 Start Download")
        self.start_cancel_btn.setObjectName("startBtn")
        self.start_cancel_btn.setMinimumWidth(180)
        self.start_cancel_btn.setStyleSheet(
            "QPushButton { color: #76e648; background-color: transparent; border: 2px solid #76e648; font-size: 15px; font-weight: 600; padding: 8px 16px; border-radius: 8px; } "
            "QPushButton:hover { background-color: rgba(118, 230, 72, 0.1); }"
        )
        buttons_layout.addWidget(self.start_cancel_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMinimumWidth(100)
        self.clear_btn.setStyleSheet(
            "QPushButton { color: #76e648; background-color: transparent; border: 2px solid #76e648; font-size: 15px; font-weight: 600; padding: 8px 16px; border-radius: 8px; } "
            "QPushButton:hover { background-color: rgba(118, 230, 72, 0.1); }"
        )
        buttons_layout.addWidget(self.clear_btn)

        self.pause_resume_btn = QPushButton("⏸️ Pause")
        self.pause_resume_btn.setObjectName("pauseBtn")
        self.pause_resume_btn.setStyleSheet(
            "QPushButton { color: #76e648; background-color: transparent; border: 2px solid #76e648; font-size: 15px; font-weight: 600; padding: 8px 16px; border-radius: 8px; } "
            "QPushButton:hover { background-color: rgba(118, 230, 72, 0.1); }"
        )
        buttons_layout.addWidget(self.pause_resume_btn)

        url_master_layout.addWidget(buttons_container)

        # 5. Bottom Horizontal Separator (Above Counter)
        bottom_sep = QFrame()
        bottom_sep.setFrameShape(QFrame.Shape.HLine)
        bottom_sep.setFixedHeight(2)
        bottom_sep.setStyleSheet("background-color: #76e648; border: none;")
        url_master_layout.addWidget(bottom_sep)

        # 6. URL Counter (Inside Master)
        self.url_count_label = QLabel("URLs: 0")
        self.url_count_label.setStyleSheet("color: #76e648; font-weight: 600; padding: 8px 15px;")
        url_master_layout.addWidget(self.url_count_label)

        # Add master to main layout
        main_layout.addWidget(url_master)
        main_layout.addSpacing(10)

        progress_group = QGroupBox("Download Progress")
        progress_group.setStyleSheet("QGroupBox { border: 1px solid #404040; border-radius: 8px; margin-top: 15px; padding-top: 15px; }")
        progress_group.setStyleSheet(progress_group.styleSheet() + " QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #888888; font-size: 13px; font-weight: 600; }")
        progress_group.setMinimumHeight(150)
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        progress_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to download...")
        self.progress_label.setStyleSheet(
            "font-size: 14px; font-weight: 500; color: #cccccc; padding: 4px 0; background-color: transparent;"
        )
        self.speed_label = QLabel("Speed: 0.0 MB/s")
        self.speed_label.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #76e648; padding: 4px 0; background-color: transparent;"
        )

        progress_layout.addWidget(self.progress_bar)

        progress_info_layout = QHBoxLayout()
        progress_info_layout.addWidget(self.progress_label)
        progress_info_layout.addStretch()
        progress_info_layout.addWidget(self.speed_label)

        progress_layout.addLayout(progress_info_layout)

        main_layout.addWidget(progress_group)

        # Activity Log Section
        log_group = QGroupBox("Activity Log")
        log_group.setStyleSheet("QGroupBox { border: 1px solid #404040; border-radius: 8px; margin-top: 15px; padding-top: 15px; }")
        log_group.setStyleSheet(log_group.styleSheet() + " QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #888888; font-size: 13px; font-weight: 600; }")
        log_group.setMinimumHeight(200)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(8)

        # Frame for the log area - NOW WITH GREEN BORDER
        log_frame = QFrame()
        log_frame.setFrameShape(QFrame.Shape.Box)
        log_frame.setFrameShadow(QFrame.Shadow.Raised)
        log_frame.setLineWidth(2)
        log_frame.setStyleSheet(
            """
            QFrame {
                border: 2px solid #76e648;
                background-color: #242424;
                border-radius: 4px;
            }
        """
        )

        log_frame_layout = QVBoxLayout(log_frame)
        log_frame_layout.setContentsMargins(5, 5, 5, 5)
        log_frame_layout.setSpacing(0)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setStyleSheet(
            "QTextEdit { background-color: #242424; color: #cccccc; border: none; padding: 8px; font-family: 'Monaco', 'Courier New', monospace; font-size: 13px; line-height: 1.4; }"
        )
        log_frame_layout.addWidget(self.log_text)

        log_layout.addWidget(log_frame)

        # Green separator line at bottom of Activity Log - FULL WIDTH
        log_bottom_separator = QFrame()
        log_bottom_separator.setFrameShape(QFrame.Shape.HLine)
        log_bottom_separator.setStyleSheet("border: none; background-color: #76e648; max-height: 1px; margin: 0px;")
        log_layout.addWidget(log_bottom_separator)

        # Removed premature log_group add to avoid duplicates

        # Green separator line above Status Bar
        bottom_separator = QFrame()
        bottom_separator.setFrameShape(QFrame.Shape.HLine)
        bottom_separator.setStyleSheet("border: none; background-color: #76e648; max-height: 1px; margin-top: 5px;")
        main_layout.addWidget(bottom_separator)

        # Stats labels at bottom
        stats_layout = QHBoxLayout()
        self.folders_label = QLabel("Folders: 0")
        self.folders_label.setStyleSheet(
            "color: #cccccc; font-size: 14px; font-weight: 500; padding: 4px 0; background-color: transparent;"
        )
        self.files_label = QLabel("Files: 0")
        self.files_label.setStyleSheet(
            "color: #cccccc; font-size: 14px; font-weight: 500; padding: 4px 0; background-color: transparent;"
        )
        self.size_label = QLabel("Size: 0 MB")
        self.size_label.setStyleSheet(
            "color: #76e648; font-size: 14px; font-weight: 600; padding: 4px 0; background-color: transparent;"
        )

        stats_layout.addWidget(self.folders_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.files_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.size_label)
        log_layout.addLayout(stats_layout)

        main_layout.addWidget(log_group)

        # Final Layout Stabilization Stretch
        main_layout.addStretch()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def setup_connections(self):
        """Connect signals and slots."""
        self.url_input.textChanged.connect(self.validate_urls)

        # Sync scrolling: Input Box -> controls -> Line Numbers
        self.url_input.verticalScrollBar().valueChanged.connect(
            self.line_numbers.verticalScrollBar().setValue
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
        current_dir = str(self.scraper.download_dir)
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Download Folder", current_dir, QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.scraper.download_dir = Path(folder)
            self.scraper.download_dir.mkdir(parents=True, exist_ok=True)
            self.add_log_message(f"📁 Download folder changed to: {folder}")
            self.status_bar.showMessage(f"Download folder: {folder}")

    def validate_urls(self):
        """Validate URLs in real-time and update line numbers"""
        if getattr(self, "_validating", False):
            return

        # 1. Capture current scroll state from the INPUT box (the driver)
        current_scroll = self.url_input.verticalScrollBar().value()

        raw_text = self.url_input.toPlainText()
        all_lines = raw_text.split("\n")
        line_count = max(1, len(all_lines))

        # 2. Update line numbers display
        # We align center and ensure distinct lines
        line_nums = "\n".join(str(i) for i in range(1, line_count + 1))

        if self.line_numbers.toPlainText() != line_nums:
            self.line_numbers.setPlainText(line_nums)
            # Robust centering for all line blocks (QPlainTextEdit safe)
            cursor = self.line_numbers.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            fmt = QTextBlockFormat()
            fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cursor.setBlockFormat(fmt)

        # 3. Dynamic height logic (Ditch expansion, keep it stable)
        # We no longer resize the master container here to prevent jitter and overlaps.
        # The master container's height is now fixed in setup_ui.
        pass

        # 4. CRITICAL FIX: Sync the scrollbars
        # Set line_numbers scroll to match the input box
        self.line_numbers.verticalScrollBar().setValue(current_scroll)

        # Count non-empty lines for URL validation
        raw_lines = [ln.strip() for ln in all_lines if ln.strip()]

        # Update the URL counter label
        self.url_count_label.setText(f"URLs: {len(raw_lines)}")

        # Validate URL count (maximum 10)
        if len(raw_lines) > 10:
            self._update_url_status(
                "⚠️ Maximum 10 URLs allowed. Please remove some URLs.", "invalid"
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

            self.scraper.download_dir = Path(folder)
            self.scraper.download_dir.mkdir(parents=True, exist_ok=True)
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

    def download_finished(self, stats: Dict):
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
            self.speed_label.setText("Speed: 0.0 MB/s")
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
            "idle": "#888888",
        }
        color = colors.get(state, "#888888")
        self.status_bar.showMessage(text)
        self.status_bar.setStyleSheet(
            f"QStatusBar {{ color: {color}; font-size: 14px; font-weight: 600; padding: 8px 0; }}"
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
        self.speed_label.setText(f"Speed: {speed:.1f} MB/s")

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
            self.folders_label.setText(f"Folders: {folder_count}")
            self.files_label.setText(f"Files: {file_count}")
            self.size_label.setText(f"Size: {size_mb:.1f} MB")

        except Exception as e:
            logger.warning(f"Could not update download stats: {e}")

    def paste_from_clipboard(self):
        """Paste URLs from clipboard with auto-formatting"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()

        if not text:
            return

        # Extract URLs using regex
        urls = re.findall(r"https?://[^\s]+", text)
        valid_urls = [
            url for url in urls if "boards.4chan.org" in url or "4chan.org" in url
        ]

        if valid_urls:
            # If we found valid URLs, paste them nicely formatted
            # Join with newlines
            paste_text = "\n".join(valid_urls) + "\n"

            cursor = self.url_input.textCursor()
            # If we're not at the start of a line, add a newline first
            if cursor.positionInBlock() > 0:
                paste_text = "\n" + paste_text

            cursor.insertText(paste_text)
            self.url_input.setTextCursor(cursor)
        else:
            # Fallback: Normal paste if no valid URLs found
            self.url_input.paste()

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

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        text = event.mimeData().text().strip()
        urls = re.findall(r"https?://[^\s]+", text)
        valid_urls = [
            url for url in urls if "boards.4chan.org" in url or "4chan.org" in url
        ]
        if valid_urls:
            # Just add URLs, no numbering
            self.url_input.setPlainText("\n".join(valid_urls))
            self.validate_urls()

if __name__ == "__main__":
    # Setup basic logging for standalone run
    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
