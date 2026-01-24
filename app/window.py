from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QSettings, QThread, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTabWidget,
    QTextEdit,
    QWidget,
)

from app.worker import TranscribeWorker, TranscriptionConfig


THEMES: dict[str, dict[str, str]] = {
    "Light": {
        "background": "#ecf1fb",
        "surface": "#ffffff",
        "surface_alt": "#dfe6f7",
        "text": "#1d2333",
        "subtext": "#4c5570",
        "muted": "#8791ac",
        "border": "#cfd7eb",
        "focus": "#4f7cff",
        "accent": "#3f6ae0",
        "accentHover": "#355bc2",
        "accentPressed": "#2c4aa0",
        "onAccent": "#f7f9ff",
        "selection": "#d4def8",
    },
    "Dark": {
        "background": "#090c18",
        "surface": "#12182b",
        "surface_alt": "#0b0f1c",
        "text": "#dfe6ff",
        "subtext": "#9aacd8",
        "muted": "#59607a",
        "border": "#1a2138",
        "focus": "#7bb0ff",
        "accent": "#4f7cff",
        "accentHover": "#6a90ff",
        "accentPressed": "#335bc7",
        "onAccent": "#f5f7ff",
        "selection": "#1a2544",
    },
}


@dataclass
class UiState:
    running: bool = False


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Transcriber")
        self.setMinimumWidth(760)

        self._thread: QThread | None = None
        self._worker: TranscribeWorker | None = None
        self._state = UiState()
        self._settings = QSettings("Sisyphus", "Transcriber")

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QGridLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        transcribe_tab = QWidget()
        transcribe_layout = QGridLayout(transcribe_tab)
        transcribe_layout.setSpacing(10)

        settings_box = QGroupBox("Settings")
        settings_layout = QGridLayout(settings_box)
        settings_layout.setHorizontalSpacing(12)
        settings_layout.setVerticalSpacing(10)
        settings_layout.setContentsMargins(12, 12, 12, 12)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste video or playlist URL")

        self.language_combo = QComboBox()
        self.language_combo.addItems(["auto", "en", "es"])

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium"])
        self.model_combo.setCurrentText("base")

        settings_layout.addWidget(QLabel("URL"), 0, 0)
        settings_layout.addWidget(self.url_input, 0, 1, 1, 3)
        settings_layout.addWidget(QLabel("Language"), 1, 0)
        settings_layout.addWidget(self.language_combo, 1, 1)
        settings_layout.addWidget(QLabel("Model"), 1, 2)
        settings_layout.addWidget(self.model_combo, 1, 3)

        action_row = QHBoxLayout()
        self.start_button = QPushButton("Transcribe")
        self.start_button.setObjectName("PrimaryButton")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.output_open_button = QPushButton("Open Output")
        self.output_open_button.setObjectName("SubtleButton")
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.output_open_button)

        self.backend_label = QLabel("Backend: -")
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setMaximum(100)
        self.progress.setTextVisible(False)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_view.setPlaceholderText("Logs will appear here as the transcription runs...")

        transcribe_layout.addWidget(settings_box, 0, 0)
        transcribe_layout.addLayout(action_row, 1, 0)
        transcribe_layout.addWidget(self.backend_label, 2, 0)
        transcribe_layout.addWidget(self.progress, 3, 0)
        transcribe_layout.addWidget(self.log_view, 4, 0)
        transcribe_layout.setRowStretch(4, 1)

        settings_tab = QWidget()
        settings_tab_layout = QGridLayout(settings_tab)
        settings_tab_layout.setHorizontalSpacing(12)
        settings_tab_layout.setVerticalSpacing(10)
        settings_tab_layout.setContentsMargins(12, 12, 12, 12)

        self.ffmpeg_input = QLineEdit()
        self.ffmpeg_input.setPlaceholderText("Path to ffmpeg.exe")
        ffmpeg_browse = QPushButton("Browse")

        self.ytdlp_input = QLineEdit()
        self.ytdlp_input.setPlaceholderText("Path to yt-dlp.exe")
        ytdlp_browse = QPushButton("Browse")

        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Output folder (optional)")
        output_browse = QPushButton("Browse")

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])


        settings_tab_layout.addWidget(QLabel("FFmpeg"), 0, 0)
        settings_tab_layout.addWidget(self.ffmpeg_input, 0, 1)
        settings_tab_layout.addWidget(ffmpeg_browse, 0, 2)
        settings_tab_layout.addWidget(QLabel("yt-dlp"), 1, 0)
        settings_tab_layout.addWidget(self.ytdlp_input, 1, 1)
        settings_tab_layout.addWidget(ytdlp_browse, 1, 2)
        settings_tab_layout.addWidget(QLabel("Output"), 2, 0)
        settings_tab_layout.addWidget(self.output_dir_input, 2, 1)
        settings_tab_layout.addWidget(output_browse, 2, 2)
        settings_tab_layout.addWidget(QLabel("Theme"), 3, 0)
        settings_tab_layout.addWidget(self.theme_combo, 3, 1, 1, 2)

        settings_tab_layout.setColumnStretch(1, 1)

        tabs.addTab(transcribe_tab, "Transcribe")
        tabs.addTab(settings_tab, "Settings")

        layout.addWidget(tabs, 0, 0)

        self.setCentralWidget(central)

        self.start_button.clicked.connect(self._on_start)
        self.cancel_button.clicked.connect(self._on_cancel)
        ffmpeg_browse.clicked.connect(self._browse_ffmpeg)
        ytdlp_browse.clicked.connect(self._browse_ytdlp)
        output_browse.clicked.connect(self._browse_output_dir)
        self.output_open_button.clicked.connect(self._open_output_dir)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        self._load_settings()
        self._apply_theme(self.theme_combo.currentText())

    def _browse_ffmpeg(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select ffmpeg",
            "",
            "Executables (*.exe);;All Files (*)",
        )
        if file_name:
            self.ffmpeg_input.setText(file_name)
            self._save_settings()

    def _browse_ytdlp(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select yt-dlp",
            "",
            "Executables (*.exe);;All Files (*)",
        )
        if file_name:
            self.ytdlp_input.setText(file_name)
            self._save_settings()

    def _browse_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select output folder",
            self.output_dir_input.text().strip() or "",
        )
        if folder:
            self.output_dir_input.setText(folder)
            self._save_settings()

    def _open_output_dir(self) -> None:
        path = self.output_dir_input.text().strip()
        if not path:
            path = str(Path.cwd() / "transcripts")
        if not Path(path).exists():
            QMessageBox.warning(self, "Missing Folder", "The output folder does not exist.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _on_start(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please provide a video or playlist URL.")
            return

        self._save_settings()
        config = TranscriptionConfig(
            url=url,
            language=self.language_combo.currentText(),
            model_name=self.model_combo.currentText(),
            ffmpeg_path=self._normalized_path(self.ffmpeg_input.text()),
            ytdlp_path=self._normalized_path(self.ytdlp_input.text()),
            output_dir=self._normalized_path(self.output_dir_input.text()),
        )
        self._start_worker(config)

    def _start_worker(self, config: TranscriptionConfig) -> None:
        if self._state.running:
            return

        self._state.running = True
        self._set_controls_enabled(False)
        self._append_log("Starting transcription...")
        self.progress.setValue(0)
        self.backend_label.setText("Backend: detecting...")

        thread = QThread(self)
        worker = TranscribeWorker(config)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.log.connect(self._append_log)
        worker.progress.connect(self._on_progress)
        worker.backend.connect(self._on_backend)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_cancel(self) -> None:
        if self._worker is None:
            return
        self._append_log("Cancellation requested...")
        self._worker.cancel()
        self.cancel_button.setEnabled(False)

    def _on_progress(self, current: int, total: int) -> None:
        if total <= 0:
            self.progress.setValue(0)
            return
        percent = int((current / total) * 100)
        self.progress.setValue(percent)

    def _on_backend(self, name: str) -> None:
        self.backend_label.setText(f"Backend: {name}")

    def _on_finished(self, success: bool, message: str) -> None:
        self._state.running = False
        self._set_controls_enabled(True)
        status = "completed" if success else "stopped"
        self._append_log(f"Transcription {status}: {message}")

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.url_input.setEnabled(enabled)
        self.language_combo.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.cancel_button.setEnabled(not enabled)

    def _load_settings(self) -> None:
        self.ffmpeg_input.setText(self._settings.value("paths/ffmpeg", ""))
        self.ytdlp_input.setText(self._settings.value("paths/ytdlp", ""))
        self.output_dir_input.setText(self._settings.value("paths/output_dir", ""))
        theme = self._settings.value("ui/theme", "System")
        if theme not in {"System", "Light", "Dark"}:
            theme = "System"
        self.theme_combo.setCurrentText(theme)

    def _save_settings(self) -> None:
        self._settings.setValue("paths/ffmpeg", self.ffmpeg_input.text().strip())
        self._settings.setValue("paths/ytdlp", self.ytdlp_input.text().strip())
        self._settings.setValue("paths/output_dir", self.output_dir_input.text().strip())

    def _on_theme_changed(self, theme: str) -> None:
        self._settings.setValue("ui/theme", theme)
        self._apply_theme(theme)

    def _apply_theme(self, theme: str) -> None:
        if theme == "System":
            self.setStyleSheet("")
            return

        colors = THEMES.get(theme, THEMES["Light"])
        self.setStyleSheet(self._build_stylesheet(colors))

    @staticmethod
    def _build_stylesheet(colors: dict[str, str]) -> str:
        # Lightweight QSS theme that keeps controls consistent across tabs.
        return f"""
* {{
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
    color: {colors['text']};
}}

QWidget {{
    background-color: {colors['background']};
}}

QGroupBox {{
    border: 1px solid {colors['border']};
    border-radius: 10px;
    margin-top: 12px;
    padding: 12px 12px 10px 12px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {colors['subtext']};
}}

QLabel {{
    color: {colors['subtext']};
}}

QLineEdit,
QComboBox {{
    background: {colors['surface']};
    border: 1px solid {colors['border']};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {colors['selection']};
    selection-color: {colors['text']};
}}

QLineEdit:focus,
QComboBox:focus {{
    border-color: {colors['focus']};
}}

QComboBox QListView {{
    background: {colors['surface']};
    border: 1px solid {colors['border']};
    selection-background-color: {colors['selection']};
    selection-color: {colors['text']};
}}

QCheckBox {{
    color: {colors['text']};
}}

QPushButton {{
    border: 1px solid {colors['border']};
    background: {colors['surface']};
    color: {colors['text']};
    border-radius: 8px;
    padding: 7px 12px;
}}

QPushButton#PrimaryButton {{
    background: {colors['accent']};
    border-color: {colors['accent']};
    color: {colors['onAccent']};
}}

QPushButton#PrimaryButton:hover {{
    background: {colors['accentHover']};
}}

QPushButton#PrimaryButton:pressed {{
    background: {colors['accentPressed']};
}}

QPushButton#SubtleButton {{
    background: transparent;
    border-color: {colors['border']};
    color: {colors['subtext']};
}}

QPushButton:disabled {{
    color: {colors['muted']};
    border-color: {colors['border']};
    background: {colors['surface_alt']};
}}

QProgressBar {{
    background: {colors['surface']};
    border: 1px solid {colors['border']};
    border-radius: 8px;
    height: 14px;
}}

QProgressBar::chunk {{
    border-radius: 7px;
    background: {colors['accent']};
}}

QTextEdit {{
    background: {colors['surface']};
    border: 1px solid {colors['border']};
    border-radius: 8px;
    padding: 8px;
    color: {colors['text']};
}}

QTabWidget::pane {{
    border: none;
}}

QTabBar::tab {{
    background: {colors['surface']};
    border: 1px solid {colors['border']};
    padding: 6px 12px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

QTabBar::tab:selected {{
    background: {colors['background']};
    color: {colors['text']};
    border-bottom-color: {colors['background']};
}}
"""
    @staticmethod
    def _normalized_path(value: str) -> str | None:
        cleaned = value.strip()
        return cleaned or None



