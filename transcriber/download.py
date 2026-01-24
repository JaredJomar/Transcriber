from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from transcriber.convert import convert_to_wav
from transcriber.system import run_command, run_json
from transcriber.types import ToolPaths, VideoItem


def download_audio(
    url: str,
    is_playlist: bool,
    output_dir: Path,
    log: Callable[[str], None],
    tools: ToolPaths,
) -> list[VideoItem]:
    try:
        import yt_dlp

        return download_with_module(url, is_playlist, output_dir, log, yt_dlp, tools)
    except ImportError:
        log("yt-dlp module not available. Falling back to CLI.")
        return download_with_cli(url, is_playlist, output_dir, log, tools)


def download_with_module(
    url: str,
    is_playlist: bool,
    output_dir: Path,
    log: Callable[[str], None],
    yt_dlp,
    tools: ToolPaths,
) -> list[VideoItem]:
    output_template = str(output_dir / "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": not is_playlist,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    log("Downloading audio with yt-dlp module...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        entries = normalize_entries(info)
        items = []
        for entry in entries:
            if entry is None:
                continue
            video_id = entry.get("id") or "unknown"
            title = entry.get("title") or video_id
            webpage_url = entry.get("webpage_url") or url
            raw_path = resolve_downloaded_path(entry, output_dir, ydl)
            if raw_path is None or not raw_path.exists():
                raw_path = find_downloaded_file(output_dir, video_id)
            if raw_path is None:
                log(f"Skipping {video_id}: downloaded file not found.")
                continue

            wav_path = output_dir / f"{video_id}.wav"
            convert_to_wav(raw_path, wav_path, log, tools)
            items.append(VideoItem(video_id=video_id, title=title, url=webpage_url, audio_path=wav_path))

        return items


def download_with_cli(
    url: str,
    is_playlist: bool,
    output_dir: Path,
    log: Callable[[str], None],
    tools: ToolPaths,
) -> list[VideoItem]:
    if tools.ytdlp is None:
        raise RuntimeError("yt-dlp CLI not found.")
    info_cmd = [tools.ytdlp, "--dump-single-json"]
    if not is_playlist:
        info_cmd.append("--no-playlist")
    info_cmd.append(url)
    info = run_json(info_cmd, log)

    output_template = str(output_dir / "%(id)s.%(ext)s")
    download_cmd = [
        tools.ytdlp,
        "-x",
        "--audio-format",
        "wav",
        "--audio-quality",
        "0",
        "-o",
        output_template,
    ]
    if not is_playlist:
        download_cmd.append("--no-playlist")
    download_cmd.append(url)

    log("Downloading audio with yt-dlp CLI...")
    run_command(download_cmd, log)

    entries = normalize_entries(info)
    items = []
    for entry in entries:
        if entry is None:
            continue
        video_id = entry.get("id") or "unknown"
        title = entry.get("title") or video_id
        webpage_url = entry.get("webpage_url") or url
        wav_path = output_dir / f"{video_id}.wav"
        if not wav_path.exists():
            log(f"Skipping {video_id}: WAV file not found.")
            continue
        items.append(VideoItem(video_id=video_id, title=title, url=webpage_url, audio_path=wav_path))

    return items


def normalize_entries(info: dict) -> Iterable[dict]:
    if "entries" in info and isinstance(info["entries"], list):
        return [entry for entry in info["entries"] if entry is not None]
    return [info]


def resolve_downloaded_path(entry: dict, output_dir: Path, ydl) -> Path | None:
    filename = entry.get("_filename")
    if filename:
        return Path(filename)

    downloads = entry.get("requested_downloads")
    if downloads:
        first = downloads[0]
        filepath = first.get("filepath") or first.get("filename")
        if filepath:
            return Path(filepath)

    try:
        return Path(ydl.prepare_filename(entry))
    except Exception:
        return None


def find_downloaded_file(output_dir: Path, video_id: str) -> Path | None:
    matches = list(output_dir.glob(f"{video_id}.*"))
    if not matches:
        return None
    return matches[0]
