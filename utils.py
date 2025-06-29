"""
Common utilities: pip-helper and yt-dlp bootstrap.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from typing import Sequence


def run_pip(args: Sequence[str]) -> bool:
    """
    Run “python -m pip …” with stdout/err suppressed.
    Returns True on success, False otherwise.
    """
    cmd = [sys.executable, "-m", "pip", *args]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:  # pragma: no cover
        sys.stderr.write(f"pip failed: {' '.join(cmd)}\n")
        return False


def ensure_yt_dlp() -> None:
    """
    Import yt_dlp or install it if missing.
    """
    if importlib.util.find_spec("yt_dlp") is None:
        if not run_pip(["install", "--upgrade", "yt-dlp"]):
            sys.stderr.write("yt-dlp install failed — aborting\n")
            sys.exit(1)
