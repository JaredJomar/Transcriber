from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class VideoItem:
    video_id: str
    title: str
    url: str
    audio_path: Path


@dataclass
class ToolPaths:
    ffmpeg: str
    ytdlp: str | None


@dataclass
class TranscriptionConfig:
    url: str
    language: str
    model_name: str
    ffmpeg_path: str | None
    ytdlp_path: str | None
    output_dir: str | None
