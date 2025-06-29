"""
Background thread that runs yt-dlp so the GUI stays responsive.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from PySide6.QtCore import QThread, Signal
import yt_dlp


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")  # strip colour codes


class DownloadWorker(QThread):
    """
    Execute yt-dlp in a thread and emit progress / log / status signals.
    """

    progress_signal: Signal = Signal(float, str)   # percent, filename
    status_signal:   Signal = Signal(str)          # Finished | Error: …
    log_signal:      Signal = Signal(str)          # raw yt-dlp log lines

    def __init__(self, urls: List[str], opts: Dict[str, Any]):
        super().__init__()
        self._urls = urls
        self._opts = opts

    # progress hook ----------------------------------------------------------
    def _hook(self, data: Dict[str, Any]):
        if data.get("status") == "downloading":
            pct_raw = _ANSI_RE.sub("", data.get("_percent_str", "").replace("%", ""))
            try:
                pct = float(pct_raw.strip() or 0)
            except ValueError:
                pct = 0.0
            name = Path(data.get("filename", "")).name
            self.progress_signal.emit(pct, name)

    # yt-dlp logger ----------------------------------------------------------
    class _QtLogger:
        def __init__(self, emit): self._emit = emit
        def debug(self, msg):     self._emit(msg)
        warning = error = debug

    # thread entry -----------------------------------------------------------
    def run(self):
        opts = dict(self._opts)
        opts.update(
            progress_hooks=[self._hook],
            logger=self._QtLogger(self.log_signal.emit),
            cleanup=True,  # delete partial files on cancel/error
        )
        try:
            yt_dlp.YoutubeDL(opts).download(self._urls)
            self.status_signal.emit("Finished")
        except Exception as exc:  # pylint: disable=broad-except
            self.status_signal.emit(f"Error: {exc}")
