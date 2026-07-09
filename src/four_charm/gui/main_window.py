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

from PySide6.QtCore import QEvent, QSize, Qt, QThread, QTimer
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
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from four_charm.core.scraper import FourChanScraper
from four_charm.core.urls import (
    MAX_QUEUE_URLS,
    dedupe_preserve_order,
    extract_supported_4chan_urls,
    format_urls_for_editor,
)
from four_charm.gui.widgets import (
    ActivityLog,
    LineNumberTextEdit,
    NeonButton,
    NeonPanel,
    StatCard,
    create_interface_icon,
)
from four_charm.gui.workers import MultiUrlDownloadWorker
from razorcore.appinfo import AboutDialog
from razorcore.updates import check_for_updates


logger = logging.getLogger("4Charm")

APP_NAME = "4Charm"
PACKAGE_NAME = "four-charm"


_BRAND_GREEN_RGB = (26 / 255, 46 / 255, 32 / 255)


def _existing_url_keys(editor: QPlainTextEdit) -> set[str]:
    return {
        line.strip().rstrip("/").lower()
        for line in editor.toPlainText().splitlines()
        if line.strip()
    }


def _build_url_paste_text(
    text_before_cursor: str, text_after_cursor: str, urls: list[str]
) -> str:
    paste_text = format_urls_for_editor(urls)
    if text_before_cursor and not text_before_cursor.endswith("\n\n"):
        paste_text = (
            "\n" + paste_text
            if text_before_cursor.endswith("\n")
            else "\n\n" + paste_text
        )
    if text_after_cursor and not text_after_cursor.startswith("\n\n"):
        paste_text += "\n" if text_after_cursor.startswith("\n") else "\n\n"
    return paste_text


def _insert_url_lines(editor: QPlainTextEdit, urls: list[str]) -> None:
    existing = _existing_url_keys(editor)
    new_urls = [
        url
        for url in dedupe_preserve_order(urls)
        if url.rstrip("/").lower() not in existing
    ]
    if not new_urls:
        return

    cursor = editor.textCursor()
    existing_text = editor.toPlainText()
    start = cursor.selectionStart()
    end = cursor.selectionEnd()
    paste_text = _build_url_paste_text(
        existing_text[:start], existing_text[end:], new_urls
    )
    cursor.insertText(paste_text)
    editor.setTextCursor(cursor)
    editor.ensureCursorVisible()
    QTimer.singleShot(0, editor.ensureCursorVisible)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("")
        self.setMinimumSize(960, 680)
        self.resize(1080, 720)
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
        QTimer.singleShot(0, self._style_native_title_bar)

    def _style_native_title_bar(self) -> None:
        """Color the native macOS title bar while preserving window controls."""
        if sys.platform != "darwin" or QApplication.platformName() != "cocoa":
            return

        try:
            import ctypes

            objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")

            objc_get_class = objc.objc_getClass
            objc_get_class.restype = ctypes.c_void_p
            objc_get_class.argtypes = [ctypes.c_char_p]

            sel_register_name = objc.sel_registerName
            sel_register_name.restype = ctypes.c_void_p
            sel_register_name.argtypes = [ctypes.c_char_p]

            send_id = ctypes.CFUNCTYPE(
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
            )(("objc_msgSend", objc))
            send_color = ctypes.CFUNCTYPE(
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_double,
                ctypes.c_double,
                ctypes.c_double,
                ctypes.c_double,
            )(("objc_msgSend", objc))
            send_void_id = ctypes.CFUNCTYPE(
                None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
            )(("objc_msgSend", objc))
            send_void_bool = ctypes.CFUNCTYPE(
                None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool
            )(("objc_msgSend", objc))
            send_void_int = ctypes.CFUNCTYPE(
                None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long
            )(("objc_msgSend", objc))

            native_view = ctypes.c_void_p(int(self.winId()))
            native_window = send_id(native_view, sel_register_name(b"window"))
            color_class = objc_get_class(b"NSColor")
            title_color = send_color(
                color_class,
                sel_register_name(b"colorWithSRGBRed:green:blue:alpha:"),
                *_BRAND_GREEN_RGB,
                1.0,
            )

            send_void_id(
                native_window,
                sel_register_name(b"setBackgroundColor:"),
                title_color,
            )
            send_void_bool(
                native_window,
                sel_register_name(b"setTitlebarAppearsTransparent:"),
                False,
            )
            send_void_int(
                native_window,
                sel_register_name(b"setTitleVisibility:"),
                1,
            )
        except Exception:
            logger.warning("Could not apply the native macOS title-bar style")

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
                logger.error(
                    f"CRITICAL: style.qss not found! Looked in {qss_path} and {fallback_path}"
                )

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(24, 12, 24, 10)
        main_layout.setSpacing(11)

        header = self._build_header()
        url_panel = self._build_url_panel()
        url_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        url_panel.setMinimumHeight(url_panel.sizeHint().height())
        progress_panel = self._build_progress_panel()
        lower_area = self._build_lower_area()

        main_layout.addWidget(header)
        main_layout.addWidget(url_panel)
        main_layout.addWidget(progress_panel)
        main_layout.addWidget(lower_area, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setProperty("statusState", "idle")

        self.status_content = QWidget()
        self.status_content.setObjectName("StatusContent")
        status_layout = QHBoxLayout(self.status_content)
        status_layout.setContentsMargins(20, 2, 20, 2)
        status_layout.setSpacing(9)

        self.status_indicator = QLabel()
        self.status_indicator.setObjectName("StatusIndicator")
        self.status_indicator.setFixedSize(10, 10)
        self.status_message = QLabel("Engine Status: Ready")
        self.status_message.setObjectName("StatusMessage")
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_message)
        status_layout.addStretch()

        self.status_bar.addWidget(self.status_content, 1)
        self.status_bar.setSizeGripEnabled(False)

    def _build_header(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("Header")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 4, 0, 10)
        layout.setSpacing(5)
        title = QLabel("4Charm")
        title.setObjectName("AppTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setToolTip("Double-click for About · Right-click for updates")
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        title.customContextMenuRequested.connect(self._show_title_context_menu)
        title.installEventFilter(self)
        self.title_label = title
        subtitle = QLabel("4chan image and WEBM downloader for macOS")
        subtitle.setObjectName("AppSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return panel

    def eventFilter(self, obj, event):  # noqa: N802 - Qt override
        """Open About when the 4Charm title is double-clicked."""
        if (
            obj is getattr(self, "title_label", None)
            and event.type() == QEvent.Type.MouseButtonDblClick
        ):
            self._show_about()
            return True
        return super().eventFilter(obj, event)

    def _show_about(self) -> None:
        """Show the standardized razorcore About dialog."""
        dialog = AboutDialog(self, APP_NAME, package_name=PACKAGE_NAME)
        dialog.exec()

    def _check_for_updates(self) -> None:
        """Check GitHub Releases for a newer 4Charm version."""
        current = QApplication.instance()
        version = current.applicationVersion() if current is not None else "0.0.0"
        result = check_for_updates(APP_NAME, version or "0.0.0")
        if result.is_error:
            QMessageBox.warning(
                self,
                "Update Check",
                f"Update check failed: {result.error}",
            )
            return
        if result.update_available:
            detail = f"New version available: {result.latest_version}"
            if result.download_url:
                detail = f"{detail}\n{result.download_url}"
            if result.release_notes:
                detail = f"{detail}\n\n{result.release_notes[:400]}"
            QMessageBox.information(self, "Update Available", detail)
        else:
            QMessageBox.information(
                self,
                "Up to Date",
                f"You are up to date (v{version}).",
            )

    def _show_title_context_menu(self, position) -> None:
        """Title context menu for About and update checking."""
        menu = QMenu(self)
        about_action = menu.addAction("About 4Charm")
        update_action = menu.addAction("Check for Updates")
        chosen = menu.exec(self.title_label.mapToGlobal(position))
        if chosen is about_action:
            self._show_about()
        elif chosen is update_action:
            self._check_for_updates()

    def _build_section_label(self, text: str) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("SectionHeader")
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(10)

        accent = QFrame()
        accent.setObjectName("SectionAccent")
        accent.setFixedSize(3, 18)

        label = QLabel(text)
        label.setObjectName("SectionLabel")

        layout.addWidget(accent)
        layout.addWidget(label)
        layout.addStretch()
        return wrapper

    def _build_url_panel(self) -> NeonPanel:
        panel = NeonPanel("UrlPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        label = self._build_section_label("URLS TO DOWNLOAD")

        self.url_input_frame = LineNumberTextEdit(panel)
        self.url_input_frame.setFixedHeight(142)
        self.url_input_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
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

        icon_size = QSize(18, 18)
        self.start_cancel_btn.setProperty("ready", False)
        self.start_cancel_btn.setIcon(create_interface_icon("play", color="#929a95"))
        self.start_cancel_btn.setIconSize(icon_size)
        self.clear_btn.setIcon(create_interface_icon("trash", color="#c7ccc8"))
        self.clear_btn.setIconSize(icon_size)
        self.folder_btn.setIcon(create_interface_icon("folder", color="#c7ccc8"))
        self.folder_btn.setIconSize(icon_size)
        self.pause_resume_btn.setIcon(create_interface_icon("pause", color="#c7ccc8"))
        self.pause_resume_btn.setIconSize(icon_size)

        button_row.addWidget(self.start_cancel_btn)
        button_row.addWidget(self.pause_resume_btn)
        button_row.addWidget(self.clear_btn)
        button_row.addWidget(self.folder_btn)

        self.url_count_label = QLabel("QUEUE: 0")
        self.url_count_label.setObjectName("QueueLabel")

        layout.addWidget(label)
        layout.addWidget(self.url_input_frame)
        layout.addSpacing(4)
        layout.addLayout(button_row)
        layout.addWidget(self.url_count_label)
        return panel

    def _build_progress_panel(self) -> NeonPanel:
        panel = NeonPanel("ProgressPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
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
        self.lower_layout.setSpacing(10)

        self.log_panel = NeonPanel("LogPanel")
        log_layout = QVBoxLayout(self.log_panel)
        log_layout.setContentsMargins(10, 8, 10, 10)
        log_layout.setSpacing(6)
        label = self._build_section_label("ACTIVITY LOG")
        self.log_text = ActivityLog()
        self.log_text.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        log_layout.addWidget(label)
        log_layout.addWidget(self.log_text)

        self.stats_panel = QWidget()
        self.stats_panel.setObjectName("StatsPanel")
        self.stats_panel.setFixedWidth(350)
        self.stats_layout = QVBoxLayout(self.stats_panel)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_layout.setSpacing(6)

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
        raw_lines = self.url_input_frame.urls()

        # Update the URL counter label
        self.url_count_label.setText(f"QUEUE: {len(raw_lines)}")

        if len(raw_lines) > MAX_QUEUE_URLS:
            self._update_url_status(
                f"Maximum {MAX_QUEUE_URLS} URLs allowed. Please remove some URLs.",
                "invalid",
            )
            self._set_start_ready(False)
            return

        if not raw_lines:
            self._set_start_ready(False)
            self._update_url_status("Engine Status: Ready", "idle")
            return

        valid_count = 0
        invalid_count = 0

        for url in raw_lines:
            clean_url = re.sub(r"^\d+\.\s*", "", url.strip())
            if self.scraper.parse_url(clean_url):
                valid_count += 1
            else:
                invalid_count += 1

        if valid_count > 0 and invalid_count == 0:
            self._set_start_ready(True)
            self._update_url_status(f"Ready to download {valid_count} threads", "valid")
        elif valid_count > 0 and invalid_count > 0:
            self._set_start_ready(True)
            self._update_url_status(
                f"Ready: {valid_count} valid, {invalid_count} invalid (will skip bad links)",
                "partial",
            )
        else:
            self._set_start_ready(False)
            self._update_url_status("Invalid 4chan URLs detected", "invalid")

    def _set_start_ready(self, ready: bool) -> None:
        """Refresh the idle Start button immediately when URL validity changes."""
        self.start_cancel_btn.setProperty("ready", ready)
        self.start_cancel_btn.setEnabled(ready)
        icon_color = "#303730" if ready else "#929a95"
        self.start_cancel_btn.setIcon(create_interface_icon("play", color=icon_color))
        self.start_cancel_btn.style().unpolish(self.start_cancel_btn)
        self.start_cancel_btn.style().polish(self.start_cancel_btn)
        self.start_cancel_btn.update()

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

        urls = self.url_input_frame.urls()
        if not urls:
            QMessageBox.critical(self, "Error", "No URLs provided")
            return

        self._set_status_message("Parsing links...", "valid")
        self.progress_label.setText("Parsing links...")
        self.add_log_message("Parsing links...")

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
            clean_url = re.sub(r"^\d+\.\s*", "", url.strip())
            parsed = self.scraper.parse_url(clean_url)
            if parsed:
                parsed_urls.append(parsed)
            else:
                self.add_log_message(f"Invalid link skipped: {clean_url}")
                self._set_status_message("Invalid link detected", "partial")

        if not parsed_urls:
            QMessageBox.critical(self, "Error", "No valid 4chan URLs found")
            self._set_status_message("Invalid 4chan URLs detected", "invalid")
            self.progress_label.setText("Ready")
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
        self.status_bar.setProperty("statusState", "valid" if total > 0 else "idle")
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
            self.pause_resume_btn.setText("Pause")
            self.pause_resume_btn.setIcon(
                create_interface_icon("pause", color="#c7ccc8")
            )
            self.pause_resume_btn.setVisible(False)
            self.validate_urls()
            self.speed_label.setText("0.0 MB/s")
        elif state == "downloading":
            self.start_cancel_btn.setText("Cancel")
            self.start_cancel_btn.setObjectName("cancelBtn")
            self.start_cancel_btn.setProperty("ready", False)
            self.start_cancel_btn.setIcon(
                create_interface_icon("cancel", color="#c7ccc8")
            )
            self.start_cancel_btn.setEnabled(True)
            self.pause_resume_btn.setText("Pause")
            self.pause_resume_btn.setIcon(create_interface_icon("pause"))
            self.pause_resume_btn.setVisible(True)
            self.is_paused = False
            if self.progress_bar.value() == 0:
                self.progress_label.setText("Downloading 0%")
        elif state == "paused":
            self.pause_resume_btn.setText("Resume")
            self.pause_resume_btn.setIcon(
                create_interface_icon("play", color="#c7ccc8")
            )

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

        valid_urls = extract_supported_4chan_urls(text)

        if valid_urls:
            existing_before = _existing_url_keys(self.url_input)
            new_urls = [
                url
                for url in dedupe_preserve_order(valid_urls)
                if url.rstrip("/").lower() not in existing_before
            ]
            if new_urls:
                _insert_url_lines(self.url_input, valid_urls)
                skipped = len(dedupe_preserve_order(valid_urls)) - len(new_urls)
                if skipped:
                    self.add_log_message(f"Skipped {skipped} duplicate link(s)")
            else:
                self.add_log_message("All pasted links were already in the queue")
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
        valid_urls = extract_supported_4chan_urls(text)
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
