from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QSettings, QThread
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

        tabs = QTabWidget()
        transcribe_tab = QWidget()
        transcribe_layout = QGridLayout(transcribe_tab)

        settings_box = QGroupBox("Settings")
        settings_layout = QGridLayout(settings_box)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste video or playlist URL")

        self.language_combo = QComboBox()
        self.language_combo.addItems(["auto", "en", "es"])

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium"])
        self.model_combo.setCurrentText("base")

        self.playlist_checkbox = QCheckBox("Playlist")

        settings_layout.addWidget(QLabel("URL"), 0, 0)
        settings_layout.addWidget(self.url_input, 0, 1, 1, 3)
        settings_layout.addWidget(QLabel("Language"), 1, 0)
        settings_layout.addWidget(self.language_combo, 1, 1)
        settings_layout.addWidget(QLabel("Model"), 1, 2)
        settings_layout.addWidget(self.model_combo, 1, 3)
        settings_layout.addWidget(self.playlist_checkbox, 2, 0, 1, 2)

        action_row = QHBoxLayout()
        self.start_button = QPushButton("Transcribe")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.cancel_button)

        self.backend_label = QLabel("Backend: -")
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setMaximum(100)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        transcribe_layout.addWidget(settings_box, 0, 0)
        transcribe_layout.addLayout(action_row, 1, 0)
        transcribe_layout.addWidget(self.backend_label, 2, 0)
        transcribe_layout.addWidget(self.progress, 3, 0)
        transcribe_layout.addWidget(self.log_view, 4, 0)

        settings_tab = QWidget()
        settings_tab_layout = QGridLayout(settings_tab)

        self.ffmpeg_input = QLineEdit()
        self.ffmpeg_input.setPlaceholderText("Path to ffmpeg.exe")
        ffmpeg_browse = QPushButton("Browse")

        self.ytdlp_input = QLineEdit()
        self.ytdlp_input.setPlaceholderText("Path to yt-dlp.exe")
        ytdlp_browse = QPushButton("Browse")

        settings_tab_layout.addWidget(QLabel("FFmpeg"), 0, 0)
        settings_tab_layout.addWidget(self.ffmpeg_input, 0, 1)
        settings_tab_layout.addWidget(ffmpeg_browse, 0, 2)
        settings_tab_layout.addWidget(QLabel("yt-dlp"), 1, 0)
        settings_tab_layout.addWidget(self.ytdlp_input, 1, 1)
        settings_tab_layout.addWidget(ytdlp_browse, 1, 2)
        settings_tab_layout.setColumnStretch(1, 1)

        tabs.addTab(transcribe_tab, "Transcribe")
        tabs.addTab(settings_tab, "Settings")

        layout.addWidget(tabs, 0, 0)

        self.setCentralWidget(central)

        self.start_button.clicked.connect(self._on_start)
        self.cancel_button.clicked.connect(self._on_cancel)
        ffmpeg_browse.clicked.connect(self._browse_ffmpeg)
        ytdlp_browse.clicked.connect(self._browse_ytdlp)

        self._load_settings()

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
            is_playlist=self.playlist_checkbox.isChecked(),
            ffmpeg_path=self._normalized_path(self.ffmpeg_input.text()),
            ytdlp_path=self._normalized_path(self.ytdlp_input.text()),
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
        self.playlist_checkbox.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.cancel_button.setEnabled(not enabled)

    def _load_settings(self) -> None:
        self.ffmpeg_input.setText(self._settings.value("paths/ffmpeg", ""))
        self.ytdlp_input.setText(self._settings.value("paths/ytdlp", ""))

    def _save_settings(self) -> None:
        self._settings.setValue("paths/ffmpeg", self.ffmpeg_input.text().strip())
        self._settings.setValue("paths/ytdlp", self.ytdlp_input.text().strip())

    @staticmethod
    def _normalized_path(value: str) -> str | None:
        cleaned = value.strip()
        return cleaned or None
