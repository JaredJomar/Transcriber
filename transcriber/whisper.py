from __future__ import annotations

from transcriber.types import VideoItem


def load_whisper_model(model_name: str, device: object, log):
    import whisper

    log(f"Loading Whisper model: {model_name}")
    return whisper.load_model(model_name, device=device)


def transcribe_item(model, item: VideoItem, language: str) -> dict:
    lang = None if language == "auto" else language
    result = model.transcribe(str(item.audio_path), language=lang, task="transcribe")
    result["_item"] = item
    return result
