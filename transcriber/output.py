from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


_INVALID_FILENAME_CHARS = re.compile(r"[<>:\"/\|?*\x00-\x1F]")


def write_transcript(transcripts_dir: Path, result: dict, model_name: str) -> None:
    item = result["_item"]
    text = result.get("text", "").strip()
    detected_language = result.get("language") or "unknown"
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    title = (item.title or "").strip()
    if not title:
        title = item.video_id

    output_path = _build_output_path(transcripts_dir, title, item.video_id)

    info_lines = [
        f"- **Video ID**: {item.video_id}",
        f"- **URL**: [{item.url}]({item.url})",
        f"- **Language**: {detected_language}",
        f"- **Model**: {model_name}",
        f"- **Transcribed**: {timestamp}",
    ]

    body = [
        f"# {title}",
        "",
        "## Video Information",
        "",
        *info_lines,
        "",
        "## Transcript",
        "",
        text,
        "",
    ]

    output_path.write_text("\n".join(body), encoding="utf-8")


def cleanup_data(data_dir: Path, log: Callable[[str], None]) -> None:
    try:
        for item in data_dir.glob("*"):
            if item.is_file():
                item.unlink()
        log("Cleaned temporary data directory.")
    except Exception as exc:  # noqa: BLE001
        log(f"Cleanup skipped: {exc}")


def _build_output_path(transcripts_dir: Path, title: str, video_id: str) -> Path:
    safe_title = _sanitize_filename(title)
    if not safe_title:
        safe_title = video_id
    candidate = transcripts_dir / f"{safe_title}.md"
    if not candidate.exists():
        return candidate

    for suffix in range(1, 1000):
        candidate = transcripts_dir / f"{safe_title}-{suffix}.md"
        if not candidate.exists():
            return candidate

    return transcripts_dir / f"{video_id}.md"


def _sanitize_filename(value: str) -> str:
    cleaned = _INVALID_FILENAME_CHARS.sub("", value)
    cleaned = cleaned.strip().rstrip(".")
    cleaned = cleaned.replace("  ", " ")
    cleaned = cleaned[:120].strip()
    return cleaned
