from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


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


def run_transcription(
    *,
    url: str,
    language: str,
    model_name: str,
    is_playlist: bool,
    ffmpeg_path: str | None,
    ytdlp_path: str | None,
    log: Callable[[str], None],
    progress: Callable[[int, int], None],
    backend: Callable[[str], None],
    cancelled: Callable[[], bool],
) -> None:
    language = language.strip().lower()
    tools = _ensure_environment(log, ffmpeg_path, ytdlp_path)
    _ensure_whisper(log)
    device, backend_name = _select_device(log)
    backend(backend_name)

    root_dir = Path.cwd()
    data_dir = root_dir / "data"
    transcripts_dir = root_dir / "transcripts"
    data_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    items = _download_audio(url, is_playlist, data_dir, log, tools)
    if not items:
        raise RuntimeError("No audio files were downloaded.")

    if cancelled():
        log("Cancelled before transcription.")
        return

    model = _load_whisper_model(model_name, device, log)

    total = len(items)
    for index, item in enumerate(items, start=1):
        if cancelled():
            log("Cancellation detected. Stopping further processing.")
            break

        progress(index - 1, total)
        log(f"Transcribing {item.video_id} ({index}/{total})...")
        result = _transcribe_item(model, item, language)
        _write_transcript(transcripts_dir, result, model_name)
        progress(index, total)
        log(f"Saved transcript for {item.video_id}.")

    _cleanup_data(data_dir, log)


def _ensure_environment(
    log: Callable[[str], None],
    ffmpeg_path: str | None,
    ytdlp_path: str | None,
) -> ToolPaths:
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10+ is required.")

    resolved_ffmpeg = _resolve_tool("ffmpeg", log)
    if ffmpeg_path:
        if not Path(ffmpeg_path).exists():
            raise RuntimeError("Configured ffmpeg path does not exist.")
        resolved_ffmpeg = ffmpeg_path
        log("Using configured ffmpeg path.")

    if resolved_ffmpeg is None:
        raise RuntimeError("Missing required tool in PATH: ffmpeg.")

    resolved_ytdlp = _resolve_tool("yt-dlp", log)
    if ytdlp_path:
        if not Path(ytdlp_path).exists():
            raise RuntimeError("Configured yt-dlp path does not exist.")
        resolved_ytdlp = ytdlp_path
        log("Using configured yt-dlp path.")

    has_module = _has_yt_dlp_module()
    if resolved_ytdlp is None and not has_module:
        raise RuntimeError("Missing required tool in PATH: yt-dlp.")

    os.environ["FFMPEG_BINARY"] = resolved_ffmpeg
    log("Environment check passed.")
    return ToolPaths(ffmpeg=resolved_ffmpeg, ytdlp=resolved_ytdlp)


def _ensure_whisper(log: Callable[[str], None]) -> None:
    try:
        import whisper  # noqa: F401

        log("Whisper already installed.")
        return
    except ImportError:
        log("Whisper not found. Installing openai-whisper...")
        _pip_install(["openai-whisper"], log)


def _ensure_torch(log: Callable[[str], None]) -> None:
    try:
        import torch  # noqa: F401

        log("PyTorch already installed.")
        return
    except ImportError:
        log("PyTorch not found. Installing...")

    if _has_nvidia_smi():
        log("NVIDIA GPU detected. Trying CUDA-enabled PyTorch install...")
        try:
            _pip_install(
                [
                    "torch",
                    "torchvision",
                    "torchaudio",
                ],
                log,
                extra_args=["--index-url", "https://download.pytorch.org/whl/cu121"],
            )
            return
        except RuntimeError:
            log("CUDA install failed. Falling back to CPU-only PyTorch.")

    _pip_install(["torch", "torchvision", "torchaudio"], log)


def _ensure_directml(log: Callable[[str], None]) -> bool:
    if sys.version_info >= (3, 12):
        log("torch-directml is not available for this Python version. Skipping.")
        return False
    try:
        import torch_directml  # noqa: F401

        log("torch-directml already installed.")
        return True
    except ImportError:
        log("torch-directml not found. Installing...")
        _pip_install(["torch-directml"], log)
        return True


def _select_device(log: Callable[[str], None]) -> tuple[object, str]:
    _ensure_torch(log)
    import torch

    if torch.cuda.is_available():
        log("Using NVIDIA CUDA backend.")
        return "cuda", "CUDA"

    try:
        if _ensure_directml(log):
            import torch_directml

            dml_device = torch_directml.device()
            if dml_device is not None:
                log("Using DirectML backend.")
                return dml_device, "DirectML"
    except Exception as exc:  # noqa: BLE001
        log(f"DirectML unavailable: {exc}")

    log("Falling back to CPU backend.")
    return "cpu", "CPU"


def _load_whisper_model(model_name: str, device: object, log: Callable[[str], None]):
    import whisper

    log(f"Loading Whisper model: {model_name}")
    return whisper.load_model(model_name, device=device)


def _download_audio(
    url: str,
    is_playlist: bool,
    output_dir: Path,
    log: Callable[[str], None],
    tools: ToolPaths,
) -> list[VideoItem]:
    try:
        import yt_dlp

        return _download_with_module(url, is_playlist, output_dir, log, yt_dlp, tools)
    except ImportError:
        log("yt-dlp module not available. Falling back to CLI.")
        return _download_with_cli(url, is_playlist, output_dir, log, tools)


def _download_with_module(
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

    entries = _normalize_entries(info)
    items = []
    for entry in entries:
        if entry is None:
            continue
        video_id = entry.get("id") or "unknown"
        title = entry.get("title") or video_id
        webpage_url = entry.get("webpage_url") or url
        raw_path = Path(output_dir / f"{video_id}.{entry.get('ext', 'webm')}")
        if not raw_path.exists():
            raw_path = _find_downloaded_file(output_dir, video_id)
        if raw_path is None:
            log(f"Skipping {video_id}: downloaded file not found.")
            continue

        wav_path = output_dir / f"{video_id}.wav"
        _convert_to_wav(raw_path, wav_path, log, tools)
        items.append(VideoItem(video_id=video_id, title=title, url=webpage_url, audio_path=wav_path))

    return items


def _download_with_cli(
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
    info = _run_json(info_cmd, log)

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
    _run_command(download_cmd, log)

    entries = _normalize_entries(info)
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


def _normalize_entries(info: dict) -> Iterable[dict]:
    if "entries" in info and isinstance(info["entries"], list):
        return [entry for entry in info["entries"] if entry is not None]
    return [info]


def _find_downloaded_file(output_dir: Path, video_id: str) -> Path | None:
    matches = list(output_dir.glob(f"{video_id}.*"))
    if not matches:
        return None
    return matches[0]


def _convert_to_wav(
    input_path: Path,
    output_path: Path,
    log: Callable[[str], None],
    tools: ToolPaths,
) -> None:
    if output_path.exists():
        return
    cmd = [
        tools.ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(output_path),
    ]
    log(f"Converting to WAV: {input_path.name}")
    _run_command(cmd, log)


def _transcribe_item(model, item: VideoItem, language: str) -> dict:
    lang = None if language == "auto" else language
    result = model.transcribe(str(item.audio_path), language=lang, task="transcribe")
    result["_item"] = item
    return result


def _write_transcript(transcripts_dir: Path, result: dict, model_name: str) -> None:
    item = result["_item"]
    text = result.get("text", "")
    detected_language = result.get("language")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    output_path = transcripts_dir / f"{item.video_id}.txt"
    header = [
        f"Title: {item.title}",
        f"Video ID: {item.video_id}",
        f"URL: {item.url}",
        f"Detected Language: {detected_language}",
        f"Model: {model_name}",
        f"Transcribed At: {timestamp}",
        "---",
        "",
    ]
    output_path.write_text("\n".join(header) + text.strip() + "\n", encoding="utf-8")


def _cleanup_data(data_dir: Path, log: Callable[[str], None]) -> None:
    try:
        for item in data_dir.glob("*"):
            if item.is_file():
                item.unlink()
        log("Cleaned temporary data directory.")
    except Exception as exc:  # noqa: BLE001
        log(f"Cleanup skipped: {exc}")


def _run_command(cmd: list[str], log: Callable[[str], None]) -> None:
    log("Running: " + " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Command failed")


def _run_json(cmd: list[str], log: Callable[[str], None]) -> dict:
    log("Running: " + " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Command failed")
    return json.loads(result.stdout)


def _pip_install(packages: list[str], log: Callable[[str], None], extra_args: list[str] | None = None) -> None:
    cmd = [sys.executable, "-m", "pip", "install", *packages]
    if extra_args:
        cmd.extend(extra_args)
    log("Installing: " + " ".join(packages))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "pip install failed")


def _has_nvidia_smi() -> bool:
    return shutil.which("nvidia-smi") is not None


def _has_yt_dlp_module() -> bool:
    try:
        import yt_dlp  # noqa: F401

        return True
    except ImportError:
        return False


def get_subprocess_no_window_kwargs() -> dict:
    if sys.platform.startswith("win"):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        except Exception:
            startupinfo = None
        flags = 0
        try:
            flags |= subprocess.CREATE_NO_WINDOW
        except Exception:
            pass
        kwargs: dict[str, object] = {}
        if startupinfo is not None:
            kwargs["startupinfo"] = startupinfo
        if flags:
            kwargs["creationflags"] = flags
        return kwargs
    return {}


def find_executable(executable_name: str) -> str | None:
    path = shutil.which(executable_name)
    if path:
        return path

    if not sys.platform.startswith("win"):
        return None

    for candidate in _get_where_candidates(executable_name):
        path = _run_where(candidate)
        if path:
            return path

    return _run_powershell_where(executable_name)


def _get_where_candidates(executable_name: str) -> list[str]:
    candidates = [executable_name]
    if not executable_name.lower().endswith(".exe"):
        candidates.append(f"{executable_name}.exe")
    return candidates


def _run_where(executable_name: str) -> str | None:
    commands = [
        ["where", executable_name],
        ["cmd", "/c", "where", executable_name],
    ]
    for cmd in commands:
        try:
            output = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                text=True,
                **get_subprocess_no_window_kwargs(),
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
        if lines:
            return lines[0]
    return None


def _run_powershell_where(executable_name: str) -> str | None:
    command = (
        f"$p=(Get-Command {executable_name} -ErrorAction SilentlyContinue).Source;"
        "if ($p) { $p }"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", command],
            stderr=subprocess.STDOUT,
            text=True,
            **get_subprocess_no_window_kwargs(),
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    output = output.strip()
    return output.splitlines()[0] if output else None


def _resolve_tool(name: str, log: Callable[[str], None]) -> str | None:
    path = find_executable(name)
    if path:
        log(f"Resolved {name} at {path}")
        return path
    return None
