from __future__ import annotations

from pathlib import Path
from typing import Callable

from transcriber.system import run_command
from transcriber.types import ToolPaths


def convert_to_wav(
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
    run_command(cmd, log)
