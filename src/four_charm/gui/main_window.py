import re
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
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
            QGroupBox { border: 2px solid #76e648; margin-top: 12px; padding-top: 8px; padding-bottom: 8px; background-color: transparent; }
            QGroupBox::title { subcontrol-origin: padding; left: 12px; padding: 0 12px; color: #76e648; font-size: 26px; font-weight: 700; }
            QLineEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #404040; border-radius: 10px; padding: 12px 16px; font-size: 16px; selection-background-color: #76e648; }
            QLineEdit:focus { border: 2px solid #76e648; background-color: #353535; }
            QTextEdit { background-color: #2d2d2d; color: #ffffff; border: 2px solid #76e648; border-radius: 0px; padding: 8px 12px; font-size: 16px; selection-background-color: #76e648; line-height: 1.4; }
            QTextEdit:focus { border: 2px solid #76e648; background-color: #353535; border-radius: 0px; }
            QLabel { color: #cccccc; font-size: 15px; }
            QPushButton { font-size: 15px; padding: 8px 16px; border-radius: 8px; border: none; min-height: 36px; font-weight: 600; }
            QPushButton:hover { background-color: #5a5a5a; }
            QPushButton:pressed { background-color: #4a4a4a; }
            QPushButton:disabled { background-color: #404040; color: #888888; }
            QPushButton#startBtn { font-size: 15px; background-color: #76e648; color: #1a1a1a; font-weight: 700; border-radius: 8px; }
            QPushButton#startBtn:disabled { background-color: #404040; color: #888888; }
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
        main_layout.setSpacing(10)

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
            "Paste or drop multiple thread URLs (one per line) to download all media files concurrently\nPress Enter to validate & count URLs | Press Ctrl+Enter to start download"
        )
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction.setStyleSheet(
            "color: #888888; font-size: 15px; margin: 15px 0; line-height: 1.5;"
        )
        main_layout.addWidget(instruction)

        url_group = QGroupBox("URLs to Download")
        url_layout = QVBoxLayout(url_group)
        url_layout.setContentsMargins(10, 10, 10, 10)
        url_layout.setSpacing(8)

        # Frame for the URL input area
        url_frame = QFrame()
        url_frame.setFrameShape(QFrame.Shape.Box)
        url_frame.setFrameShadow(QFrame.Shadow.Raised)
        url_frame.setLineWidth(1)
        url_frame.setStyleSheet(
            """
            QFrame {
                border: 1px solid #404040;
                border-radius: 10px;
                background-color: #2d2d2d;
            }
        """
        )

        url_frame_layout = QVBoxLayout(url_frame)
        url_frame_layout.setContentsMargins(5, 5, 5, 5)
        url_frame_layout.setSpacing(0)

        # URL input area
        self.url_input = QTextEdit()
        self.url_input.setAcceptRichText(False)
        self.url_input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.url_input.setPlaceholderText(
            "Enter thread URLs here, one per line...\n\n"
            "Examples:\n"
            "https://boards.4chan.org/g/thread/123456789\n"
            "https://boards.4channel.org/vg/thread/987654321"
        )

        # ✅ FIX: Set minimum and maximum height for proper scrolling
        self.url_input.setMinimumHeight(150)
        self.url_input.setMaximumHeight(200)
        self.url_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # ✅ FIX: Ensure scrollbar is always visible when needed
        self.url_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # ✅ FIX: Remove document margins to prevent vertical centering
        self.url_input.document().setDocumentMargin(0)

        # ✅ FIX: Updated stylesheet with explicit scrollbar arrows
        self.url_input.setStyleSheet(
            """
    QTextEdit {
        background-color: #2b2b2b;
        color: #ffffff;
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        padding: 8px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 10pt;
        selection-background-color: #4a4a4a;
    }

    /* Scrollbar track */
    QScrollBar:vertical {
        background: #2b2b2b;
        width: 16px;
        margin: 0;
    }

    /* Scrollbar handle */
    QScrollBar::handle:vertical {
        background: #4a4a4a;
        min-height: 20px;
        border-radius: 3px;
    }

    /* ✅ FIX: UP arrow button */
    QScrollBar::sub-line:vertical {
        height: 16px;
        subcontrol-position: top;
        subcontrol-origin: margin;
        image: url(none);
        background: #3a3a3a;
        border-top: 1px solid #3a3a3a;
    }

    /* ✅ FIX: DOWN arrow button */
    QScrollBar::add-line:vertical {
        height: 16px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
        image: url(none);
        background: #3a3a3a;
        border-bottom: 1px solid #3a3a3a;
    }

    /* Arrow button hover states */
    QScrollBar::sub-line:vertical:hover, QScrollBar::add-line:vertical:hover {
        background: #5a5a5a;
    }

    /* Scrollbar space above/below handle */
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
"""
        )
        url_frame_layout.addWidget(self.url_input)

        url_layout.addWidget(url_frame)

        # URL counter label at bottom
        self.url_count_label = QLabel("URLs: 0")
        self.url_count_label.setStyleSheet(
            "color: #cccccc; font-size: 14px; font-weight: 500; padding: 4px 0; background-color: transparent;"
        )
        url_layout.addWidget(self.url_count_label)

        main_layout.addWidget(url_group)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(15)
        control_layout.addStretch()

        # Folder chooser button
        self.folder_btn = QPushButton("📁 Choose Folder")
        self.folder_btn.setMinimumWidth(150)
        self.folder_btn.setStyleSheet(
            "color: #76e648; background-color: transparent; border: 2px solid #76e648; font-size: 15px; font-weight: 600; padding: 8px 16px; border-radius: 8px;"
        )
        control_layout.addWidget(self.folder_btn)

        self.start_cancel_btn = QPushButton("🚀 Start Download")
        self.start_cancel_btn.setObjectName("startBtn")
        self.start_cancel_btn.setMinimumWidth(180)
        self.start_cancel_btn.setStyleSheet(
            "background-color: #76e648; color: #1a1a1a; font-size: 15px; font-weight: 700; padding: 8px 16px; border-radius: 8px;"
        )
        control_layout.addWidget(self.start_cancel_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMinimumWidth(100)
        self.clear_btn.setStyleSheet(
            "color: #76e648; background-color: transparent; border: 2px solid #76e648; font-size: 15px; font-weight: 600; padding: 8px 16px; border-radius: 8px;"
        )
        control_layout.addWidget(self.clear_btn)
        self.pause_resume_btn = QPushButton("⏸️ Pause")
        self.pause_resume_btn.setObjectName("pauseBtn")
        control_layout.addWidget(self.pause_resume_btn)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        progress_group = QGroupBox("Download Progress")
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

        log_group = QGroupBox("Activity Log")
        log_group.setMinimumHeight(200)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(8)

        # Frame for the log area
        log_frame = QFrame()
        log_frame.setFrameShape(QFrame.Shape.Box)
        log_frame.setFrameShadow(QFrame.Shadow.Raised)
        log_frame.setLineWidth(1)
        log_frame.setStyleSheet(
            """
            QFrame {
                border: 1px solid #404040;
                border-radius: 10px;
                background-color: #242424;
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

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def setup_connections(self):
        """Connect signals and slots."""
        self.url_input.textChanged.connect(self.validate_urls)
        self.start_cancel_btn.clicked.connect(self.handle_start_cancel_click)
        self.pause_resume_btn.clicked.connect(self.toggle_pause_resume)
        self.clear_btn.clicked.connect(self.clear_urls)
        self.folder_btn.clicked.connect(self.choose_download_folder)

        self.paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self.paste_shortcut.activated.connect(self.paste_from_clipboard)
        self.start_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self.url_input)
        self.start_shortcut.activated.connect(
            self.validate_urls
        )  # Trigger validation on Enter
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
        """Validate and auto-number URLs in real-time"""
        # ✅ FIX: Save current scroll position
        scrollbar = self.url_input.verticalScrollBar()
        scroll_pos = scrollbar.value()

        if getattr(self, "_renumbering", False):
            return  # avoid recursion while renumbering

        raw_text = self.url_input.toPlainText().strip()
        raw_lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]

        # Strip any existing leading numbering (e.g. "1. ")
        cleaned_urls: list[str] = [re.sub(r"^\d+\.\s*", "", ln) for ln in raw_lines]

        # Auto-number
        numbered_lines = [f"{i + 1}. {u}" for i, u in enumerate(cleaned_urls)]
        numbered_text = "\n".join(numbered_lines)

        # Replace text only if different to prevent cursor flicker
        if numbered_text != raw_text:
            self._renumbering = True
            self.url_input.setPlainText(numbered_text)
            cursor = self.url_input.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.url_input.setTextCursor(cursor)
            self._renumbering = False
            self._scroll_url_input_to_end()

        urls = cleaned_urls

        # Update the URL counter label
        self.url_count_label.setText(f"URLs: {len(cleaned_urls)}")

        # ✅ FIX: Validate URL count (maximum 10)
        if len(cleaned_urls) > 10:
            self._update_url_status(
                "⚠️ Maximum 10 URLs allowed. Please remove some URLs.", "invalid"
            )
            self.start_cancel_btn.setEnabled(False)
            return

        # ✅ FIX: Restore scroll position after validation
        scrollbar.setValue(scroll_pos)

        # ✅ FIX: If only one URL, ensure it's visible
        if len(raw_lines) == 1 and raw_lines[0].strip():
            self.url_input.ensureCursorVisible()

        if not urls:
            self.start_cancel_btn.setEnabled(False)
            return

        valid_count = 0
        invalid_count = 0
        temp_scraper = FourChanScraper()

        for url in urls:
            parsed_url = temp_scraper.parse_url(url)
            logger.info(f"Validating URL: {url}")
            logger.info(f"Parsed URL: {parsed_url}")
            if parsed_url:
                valid_count += 1
                logger.info(f"Valid URL: {url}")
            else:
                invalid_count += 1
                logger.warning(f"Invalid URL: {url}")

        logger.info(
            f"Validation complete: {valid_count} valid, {invalid_count} invalid"
        )

        if valid_count > 0:
            self.start_cancel_btn.setEnabled(True)
        else:
            self.start_cancel_btn.setEnabled(False)

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
            numbered_urls = [f"{i + 1}. {url}" for i, url in enumerate(valid_urls)]
            self.url_input.setPlainText("\n".join(numbered_urls))
            self._scroll_url_input_to_end()
            self.validate_urls()  # Trigger validation after drop

    def _scroll_url_input_to_end(self):
        """Scroll URL input to the newest entry so users can see recent additions."""
        # Use QTimer to ensure scrollbar maximum is calculated after text layout
        QTimer.singleShot(0, self._do_scroll_to_end)

    def _do_scroll_to_end(self):
        """Actually perform the scroll to end operation."""
        cursor = self.url_input.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.url_input.setTextCursor(cursor)
        self.url_input.ensureCursorVisible()
        scrollbar = self.url_input.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())
