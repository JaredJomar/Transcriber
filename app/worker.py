from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from transcriber.pipeline import run_transcription


@dataclass
class TranscriptionConfig:
    url: str
    language: str
    model_name: str
    is_playlist: bool
    ffmpeg_path: str | None
    ytdlp_path: str | None


class TranscribeWorker(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    backend = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, config: TranscriptionConfig) -> None:
        super().__init__()
        self._config = config
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _is_cancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        def log(message: str) -> None:
            self.log.emit(message)

        def progress(current: int, total: int) -> None:
            self.progress.emit(current, total)

        def backend(name: str) -> None:
            self.backend.emit(name)

        try:
            run_transcription(
                url=self._config.url,
                language=self._config.language,
                model_name=self._config.model_name,
                is_playlist=self._config.is_playlist,
                ffmpeg_path=self._config.ffmpeg_path,
                ytdlp_path=self._config.ytdlp_path,
                log=log,
                progress=progress,
                backend=backend,
                cancelled=self._is_cancelled,
            )
        except Exception as exc:  # noqa: BLE001 - surface error to UI
            self.log.emit(f"Error: {exc}")
            self.finished.emit(False, str(exc))
            return

        if self._cancelled:
            self.finished.emit(False, "Cancelled")
        else:
            self.finished.emit(True, "Completed")
