from __future__ import annotations

from pathlib import Path
from typing import Callable

from transcriber.download import download_audio
from transcriber.env import ensure_environment, ensure_whisper, select_device
from transcriber.output import cleanup_data, write_transcript
from transcriber.whisper import load_whisper_model, transcribe_item


def run_transcription(
    *,
    url: str,
    language: str,
    model_name: str,
    ffmpeg_path: str | None,
    ytdlp_path: str | None,
    output_dir: str | None,
    log: Callable[[str], None],
    progress: Callable[[int, int], None],
    backend: Callable[[str], None],
    cancelled: Callable[[], bool],
) -> None:
    language = language.strip().lower()
    tools = ensure_environment(log, ffmpeg_path, ytdlp_path)
    ensure_whisper(log)
    device, backend_name = select_device(log)
    backend(backend_name)

    root_dir = Path.cwd()
    data_dir = root_dir / "data"
    if output_dir:
        transcripts_dir = Path(output_dir)
    else:
        transcripts_dir = root_dir / "transcripts"
    data_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    items = download_audio(url, data_dir, log, tools)
    if not items:
        raise RuntimeError("No audio files were downloaded.")

    if cancelled():
        log("Cancelled before transcription.")
        return

    model = load_whisper_model(model_name, device, log)

    total = len(items)
    for index, item in enumerate(items, start=1):
        if cancelled():
            log("Cancellation detected. Stopping further processing.")
            break

        progress(index - 1, total)
        log(f"Transcribing {item.video_id} ({index}/{total})...")
        result = transcribe_item(model, item, language)
        write_transcript(transcripts_dir, result, model_name)
        progress(index, total)
        log(f"Saved transcript for {item.video_id}.")

    cleanup_data(data_dir, log)
