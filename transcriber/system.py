from __future__ import annotations

import json
import subprocess
import sys
from typing import Callable


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


def run_command(cmd: list[str], log: Callable[[str], None], *, hide_window_kwargs: dict | None = None) -> None:
    log("Running: " + " ".join(cmd))
    if hide_window_kwargs is None:
        hide_window_kwargs = get_subprocess_no_window_kwargs()
    result = subprocess.run(cmd, capture_output=True, text=True, **hide_window_kwargs)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Command failed")


def run_json(cmd: list[str], log: Callable[[str], None], *, hide_window_kwargs: dict | None = None) -> dict:
    log("Running: " + " ".join(cmd))
    if hide_window_kwargs is None:
        hide_window_kwargs = get_subprocess_no_window_kwargs()
    result = subprocess.run(cmd, capture_output=True, text=True, **hide_window_kwargs)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Command failed")
    return json.loads(result.stdout)


def pip_install(packages: list[str], log: Callable[[str], None], *, extra_args: list[str] | None = None) -> None:
    cmd = [sys.executable, "-m", "pip", "install", *packages]
    if extra_args:
        cmd.extend(extra_args)
    log("Installing: " + " ".join(packages))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        **get_subprocess_no_window_kwargs(),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "pip install failed")
