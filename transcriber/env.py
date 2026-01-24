from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

from transcriber.system import pip_install
from transcriber.types import ToolPaths


def ensure_environment(
    log: Callable[[str], None],
    ffmpeg_path: str | None,
    ytdlp_path: str | None,
) -> ToolPaths:
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10+ is required.")

    resolved_ffmpeg = resolve_tool("ffmpeg", log)
    if ffmpeg_path:
        if not Path(ffmpeg_path).exists():
            raise RuntimeError("Configured ffmpeg path does not exist.")
        resolved_ffmpeg = ffmpeg_path
        log("Using configured ffmpeg path.")

    if resolved_ffmpeg is None:
        raise RuntimeError("Missing required tool in PATH: ffmpeg.")

    resolved_ytdlp = resolve_tool("yt-dlp", log)
    if ytdlp_path:
        if not Path(ytdlp_path).exists():
            raise RuntimeError("Configured yt-dlp path does not exist.")
        resolved_ytdlp = ytdlp_path
        log("Using configured yt-dlp path.")

    has_module = has_yt_dlp_module()
    if resolved_ytdlp is None and not has_module:
        raise RuntimeError("Missing required tool in PATH: yt-dlp.")

    os.environ["FFMPEG_BINARY"] = resolved_ffmpeg
    _prepend_to_path(resolved_ffmpeg)
    log("Environment check passed.")
    return ToolPaths(ffmpeg=resolved_ffmpeg, ytdlp=resolved_ytdlp)


def ensure_whisper(log: Callable[[str], None]) -> None:
    try:
        import whisper  # noqa: F401

        log("Whisper already installed.")
        return
    except ImportError:
        log("Whisper not found. Installing openai-whisper...")
        pip_install(["openai-whisper"], log)


def ensure_torch(log: Callable[[str], None]) -> None:
    try:
        import torch  # noqa: F401

        log("PyTorch already installed.")
        return
    except ImportError:
        log("PyTorch not found. Installing...")

    if has_nvidia_smi():
        log("NVIDIA GPU detected. Trying CUDA-enabled PyTorch install...")
        try:
            pip_install(
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

    pip_install(["torch", "torchvision", "torchaudio"], log)


def ensure_directml(log: Callable[[str], None]) -> bool:
    if sys.version_info >= (3, 12):
        log("torch-directml is not available for this Python version. Skipping.")
        return False
    try:
        import torch_directml  # noqa: F401

        log("torch-directml already installed.")
        return True
    except ImportError:
        log("torch-directml not found. Installing...")
        pip_install(["torch-directml"], log)
        return True


def select_device(log: Callable[[str], None]) -> tuple[object, str]:
    ensure_torch(log)
    import torch

    if torch.cuda.is_available():
        log("Using NVIDIA CUDA backend.")
        return "cuda", "CUDA"

    try:
        if ensure_directml(log):
            import torch_directml

            dml_device = torch_directml.device()
            if dml_device is not None:
                log("Using DirectML backend.")
                return dml_device, "DirectML"
    except Exception as exc:  # noqa: BLE001
        log(f"DirectML unavailable: {exc}")

    log("Falling back to CPU backend.")
    return "cpu", "CPU"


def has_nvidia_smi() -> bool:
    return shutil.which("nvidia-smi") is not None


def has_yt_dlp_module() -> bool:
    try:
        import yt_dlp  # noqa: F401

        return True
    except ImportError:
        return False


def _prepend_to_path(executable_path: str) -> None:
    folder = str(Path(executable_path).parent)
    if not folder:
        return
    current = os.environ.get("PATH", "")
    entries = current.split(os.pathsep) if current else []
    if folder in entries:
        return
    os.environ["PATH"] = folder + os.pathsep + current


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

    for candidate in get_where_candidates(executable_name):
        path = run_where(candidate)
        if path:
            return path

    return run_powershell_where(executable_name)


def get_where_candidates(executable_name: str) -> list[str]:
    candidates = [executable_name]
    if not executable_name.lower().endswith(".exe"):
        candidates.append(f"{executable_name}.exe")
    return candidates


def run_where(executable_name: str) -> str | None:
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


def run_powershell_where(executable_name: str) -> str | None:
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


def resolve_tool(name: str, log: Callable[[str], None]) -> str | None:
    path = find_executable(name)
    if path:
        log(f"Resolved {name} at {path}")
        return path
    return None
