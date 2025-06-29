"""
yt-dlp GUI

• FIFO job queue (“Queue” tab)
• Basic / Advanced / Post-proc / SponsorBlock tabs
• NEW “Sites” tab (last) – searchable list of *all* yt-dlp supported sites
• System-tray minimise + desktop notifications
• Clipboard paste, open-folder, dark / light themes
• Playlist-range selector, per-category SponsorBlock, filename-template builder
• Larger spin-boxes, ANSI-safe progress, robust error dialogs
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

from PySide6.QtCore import Qt, QSettings, Slot, QSize, QUrl
from PySide6.QtGui import QAction, QGuiApplication, QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QProgressBar, QSpinBox, QSplitter,
    QStyle, QSystemTrayIcon, QTabWidget, QTextEdit, QToolBar, QVBoxLayout,
    QWidget, QMenu,
)

from job_queue import JobQueue
from template_builder import TemplateBuilderDialog
from utils import ensure_yt_dlp, run_pip
from supported_sites import SUPPORTED_SITES
import theme


class MainWindow(QMainWindow):
    """Main application window."""

    # ---------------------------------------------------------------- init
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("yt-dlp GUI")
        self.resize(1_200, 780)

        ensure_yt_dlp()

        if shutil.which("ffmpeg") is None:
            QMessageBox.warning(
                self, "FFmpeg missing",
                "ffmpeg not found in PATH – post-processing may fail.",
            )

        st = self.style()
        self.icon_open     = st.standardIcon(QStyle.SP_DirOpenIcon)
        self.icon_start    = st.standardIcon(QStyle.SP_MediaPlay)
        self.icon_stop     = st.standardIcon(QStyle.SP_MediaStop)
        self.icon_settings = st.standardIcon(QStyle.SP_FileDialogDetailedView)
        self.icon_clip     = st.standardIcon(QStyle.SP_DialogOpenButton)
        self.icon_folder   = st.standardIcon(QStyle.SP_DirIcon)

        self._settings = QSettings("yt_dlp_gui", "prefs")

        # ---------- job queue ------------------------------------------------
        self.queue = JobQueue(max_parallel=1)
        self.queue.job_updated.connect(self._refresh_queue_view)
        self.queue.message.connect(self._log_message)
        self.queue.queue_empty.connect(
            lambda: self.tray_icon.showMessage("yt-dlp GUI", "All downloads complete!")
        )

        # ---------- central layout ------------------------------------------
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(8, 8, 8, 8)

        # ---------- toolbar --------------------------------------------------
        bar = QToolBar(iconSize=QSize(16, 16)); self.addToolBar(bar)

        dark_act  = QAction("Dark",  self, checkable=True, checked=True)
        light_act = QAction("Light", self, checkable=True)
        dark_act.toggled.connect(
            lambda st: QApplication.instance().setStyleSheet(theme.DARK if st else theme.LIGHT))
        light_act.triggered.connect(lambda: dark_act.setChecked(False))
        bar.addActions((dark_act, light_act)); bar.addSeparator()

        bar.addAction(QAction(self.icon_settings, "Update yt-dlp", self, triggered=self._self_update))

        paste_act = QAction(self.icon_clip, "Paste clipboard URL", self,
                            triggered=self._paste_clipboard, shortcut="Ctrl+V")
        bar.addAction(paste_act)

        self.open_folder_act = QAction(self.icon_folder, "Open output folder", self,
                                       enabled=False, triggered=self._open_output_folder)
        bar.addAction(self.open_folder_act); bar.addSeparator()

        bar.addWidget(QLabel("Parallel:"))
        concur = QComboBox(); concur.addItems([str(i) for i in range(1, 5)])
        concur.currentIndexChanged.connect(lambda i: setattr(self.queue, "_max_parallel", i + 1))
        bar.addWidget(concur)

        # ---------- tab widget ----------------------------------------------
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 8)
        self._build_queue_tab()
        self._build_basic()
        self._build_advanced()
        self._build_postproc()
        self._build_sponsorblock()
        self._build_sites_tab()             # last tab

        # ---------- progress + log splitter ---------------------------------
        split = QSplitter(Qt.Orientation.Vertical)
        self.progress_bar = QProgressBar(alignment=Qt.AlignmentFlag.AlignCenter)
        self.log_view = QTextEdit(readOnly=True)
        split.addWidget(self.progress_bar); split.addWidget(self.log_view); split.setStretchFactor(1, 5)
        root.addWidget(split, 5)

        # ---------- bottom buttons ------------------------------------------
        btn_row = QHBoxLayout()
        self.start_btn  = QPushButton(self.icon_start, "Add to Queue", clicked=self._start_download,
                                      shortcut="Ctrl+Return")
        self.cancel_btn = QPushButton(self.icon_stop,  "Cancel Selected", clicked=self._cancel_download,
                                      enabled=False)
        btn_row.addWidget(self.start_btn); btn_row.addWidget(self.cancel_btn); btn_row.addStretch()
        root.addLayout(btn_row)

        # ---------- system tray ---------------------------------------------
        self.tray_icon = QSystemTrayIcon(self.icon_start, self)
        tray_menu = QMenu(); tray_menu.addAction("Show", self.showNormal); tray_menu.addSeparator()
        tray_menu.addAction("Quit", QApplication.instance().quit)
        self.tray_icon.setContextMenu(tray_menu); self.tray_icon.show()

        self.setAcceptDrops(True)
        QApplication.instance().setStyleSheet(theme.DARK)

    # ================================================================= sites tab
    def _build_sites_tab(self):
        tab = QWidget(); lay = QVBoxLayout(tab); lay.setContentsMargins(6, 6, 6, 6)

        self.site_search = QLineEdit(placeholderText="Search sites…")
        self.site_search.textChanged.connect(self._filter_sites)
        self.site_list = QListWidget()
        self.site_list.itemDoubleClicked.connect(self._open_site)
        lay.addWidget(self.site_search); lay.addWidget(self.site_list)

        # build internal list (display text + url)
        self._all_sites: List[tuple[str, str]] = []
        for name, url in SUPPORTED_SITES:
            host = urlparse(url).netloc or url.replace("https://", "")
            self._all_sites.append((f"{name} ({host})", url))
        self._filter_sites("")   # initial populate

        self.tabs.addTab(tab, "Sites")

    def _filter_sites(self, txt: str):
        txt = txt.lower()
        self.site_list.clear()
        for disp, url in self._all_sites:
            if txt in disp.lower():
                item = QListWidgetItem(disp)
                item.setData(Qt.ItemDataRole.UserRole, url)
                self.site_list.addItem(item)

    def _open_site(self, item):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url: QDesktopServices.openUrl(QUrl(url))

    # ================================================================= queue tab
    def _build_queue_tab(self):
        self.queue_widget = QListWidget()
        self.tabs.addTab(self.queue_widget, "Queue")

    # ================================================================= Drag & Drop / Clipboard
    def dragEnterEvent(self, e):  # noqa: N802
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self, e):  # noqa: N802
        self._append_urls([u.toString() for u in e.mimeData().urls()])
    def _paste_clipboard(self):
        txt = QGuiApplication.clipboard().text().strip()
        if txt: self._append_urls([txt])
    def _append_urls(self, urls: List[str]):
        cur = self.urls_edit.toPlainText().rstrip()
        self.urls_edit.setPlainText(cur + ("\n" if cur else "") + "\n".join(urls))

    # ================================================================= Basic tab
    def _build_basic(self):
        gb = QGroupBox("Essential")
        lay = QFormLayout(gb)

        self.urls_edit = QTextEdit(placeholderText="Paste or drag URLs here")
        lay.addRow("URLs:", self.urls_edit)

        folder_row = QHBoxLayout()
        self.out_edit = QLineEdit(self._settings.value("last_dir", str(Path.home())))
        folder_row.addWidget(self.out_edit, 9)
        folder_row.addWidget(QPushButton(self.icon_open, "", clicked=lambda: self._choose_dir(self.out_edit)), 1)
        lay.addRow("Folder:", folder_row.parentWidget() or folder_row)

        tpl_row = QHBoxLayout()
        self.tmpl_edit = QLineEdit("%(title)s.%(ext)s")
        tpl_row.addWidget(self.tmpl_edit, 9)
        tpl_row.addWidget(QPushButton("Build…", clicked=self._open_tpl_builder), 1)
        lay.addRow("Template:", tpl_row.parentWidget() or tpl_row)

        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["best video+audio", "audio only", "720p", "1080p", "custom"])
        self.fmt_custom = QLineEdit(enabled=False)
        self.fmt_combo.currentIndexChanged.connect(lambda i: self.fmt_custom.setEnabled(i == 4))
        fmt_row = QHBoxLayout(); fmt_row.addWidget(self.fmt_combo, 5); fmt_row.addWidget(self.fmt_custom, 5)
        lay.addRow("Format:", fmt_row.parentWidget() or fmt_row)

        num_row = QHBoxLayout()
        self.prefix_chk = QCheckBox("Add index")
        self.prefix_digits = QSpinBox(minimum=2, maximum=6, value=2, enabled=False)
        for sp in (self.prefix_digits,):
            sp.setButtonSymbols(QSpinBox.PlusMinus); sp.setMinimumWidth(80); sp.setAccelerated(True)
        self.prefix_chk.stateChanged.connect(lambda s: self.prefix_digits.setEnabled(bool(s)))
        num_row.addWidget(self.prefix_chk); num_row.addWidget(self.prefix_digits)
        lay.addRow("Playlist:", num_row.parentWidget() or num_row)

        self.tabs.addTab(gb, "Basic")

    # ================================================================= Advanced tab
    def _build_advanced(self):
        gb = QGroupBox("Network & misc")
        f = QFormLayout(gb)

        self.proxy_edit, self.cookies_edit, self.ua_edit = QLineEdit(), QLineEdit(), QLineEdit()
        cook_btn = QPushButton("…", clicked=lambda: self._choose_file(self.cookies_edit))
        cook_row = QHBoxLayout(); cook_row.addWidget(self.cookies_edit, 9); cook_row.addWidget(cook_btn, 1)

        f.addRow("Proxy URL:", self.proxy_edit)
        f.addRow("Cookies file:", cook_row.parentWidget() or cook_row)
        f.addRow("User-Agent:", self.ua_edit)

        rng_row = QHBoxLayout()
        self.pl_start, self.pl_end = QSpinBox(maximum=99999), QSpinBox(maximum=99999)
        for sp in (self.pl_start, self.pl_end):
            sp.setButtonSymbols(QSpinBox.PlusMinus); sp.setMinimumWidth(80); sp.setAccelerated(True)
        self.pl_start.setSpecialValueText("Start"); self.pl_end.setSpecialValueText("End")
        self.pl_start.setToolTip("Leave at “Start” for the first video.")
        self.pl_end.setToolTip(  "Leave at “End” for the last video.")
        rng_row.addWidget(self.pl_start); rng_row.addWidget(QLabel("to")); rng_row.addWidget(self.pl_end)
        f.addRow("Playlist range:", rng_row.parentWidget() or rng_row)

        self.chk_ignore = QCheckBox("Ignore errors"); self.chk_skip = QCheckBox("Skip existing")
        flags = QHBoxLayout(); flags.addWidget(self.chk_ignore); flags.addWidget(self.chk_skip)
        f.addRow("Flags:", flags.parentWidget() or flags)

        self.extra_args = QLineEdit(); f.addRow("Extra yt-dlp args:", self.extra_args)
        self.tabs.addTab(gb, "Advanced")

    # ================================================================= Post-proc tab
    def _build_postproc(self):
        gb = QGroupBox("Post-processing")
        f = QFormLayout(gb)

        self.chk_extract = QCheckBox("Extract audio"); self.audio_fmt = QComboBox()
        self.audio_fmt.addItems(["mp3", "m4a", "flac", "opus", "wav"])
        row = QHBoxLayout(); row.addWidget(self.chk_extract); row.addWidget(self.audio_fmt)
        f.addRow("Audio:", row.parentWidget() or row)

        self.chk_thumb = QCheckBox("Thumbnail"); self.chk_subs = QCheckBox("Subtitles")
        self.chk_split = QCheckBox("Split chapters")
        ex_row = QHBoxLayout(); ex_row.addWidget(self.chk_thumb); ex_row.addWidget(self.chk_subs); ex_row.addWidget(self.chk_split)
        f.addRow("Extras:", ex_row.parentWidget() or ex_row)
        self.tabs.addTab(gb, "Post-proc")

    # ================================================================= SponsorBlock tab
    def _build_sponsorblock(self):
        gb = QGroupBox("SponsorBlock")
        v = QVBoxLayout(gb)
        self.sb_enable = QCheckBox("Enable SponsorBlock"); v.addWidget(self.sb_enable)
        self.sb_enable.stateChanged.connect(lambda st: self._toggle_sb(bool(st)))

        cats = [("sponsor", "Sponsor"), ("intro", "Intro"), ("outro", "Outro"),
                ("selfpromo", "Self-promo"), ("interaction", "Interaction"),
                ("music_offtopic", "Music"), ("preview", "Preview"), ("filler", "Filler")]
        grid = QGridLayout(); v.addLayout(grid)
        grid.addWidget(QLabel("Segment"), 0, 0); grid.addWidget(QLabel("Action"), 0, 1)
        self.sb_combo: Dict[str, QComboBox] = {}
        for r, (k, lbl) in enumerate(cats, start=1):
            grid.addWidget(QLabel(lbl), r, 0)
            cmb = QComboBox(enabled=False); cmb.addItems(["None", "Remove", "Mark", "Cut"])
            grid.addWidget(cmb, r, 1); self.sb_combo[k] = cmb

        self.sb_title, self.sb_defaults = QLineEdit(enabled=False), QLineEdit(enabled=False)
        v.addWidget(QLabel("Chapter-title template:")); v.addWidget(self.sb_title)
        v.addWidget(QLabel("Raw default options:"));   v.addWidget(self.sb_defaults)
        self.tabs.addTab(gb, "SponsorBlock")

    # ================================================================= Helpers
    def _choose_dir(self, le: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "Select folder")
        if d: le.setText(d)
    def _choose_file(self, le: QLineEdit):
        f, _ = QFileDialog.getOpenFileName(self, "Select file")
        if f: le.setText(f)
    def _open_tpl_builder(self):
        dlg = TemplateBuilderDialog(self)
        if dlg.exec(): self.tmpl_edit.setText(dlg.template_string())
    def _open_output_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.out_edit.text()))
    def _toggle_sb(self, en: bool):
        for cmb in self.sb_combo.values(): cmb.setEnabled(en)
        self.sb_title.setEnabled(en); self.sb_defaults.setEnabled(en)
    def _log_message(self, txt: str):
        self.log_view.append(txt)
        if txt.startswith("Error"): QMessageBox.critical(self, "yt-dlp error", txt)
    def _self_update(self):
        if run_pip(["install", "--upgrade", "yt-dlp"]):
            QMessageBox.information(self, "Done", "yt-dlp upgraded!")

    # ================================================================= Queue actions
    @Slot()
    def _start_download(self):
        urls = [u.strip() for u in self.urls_edit.toPlainText().splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "Missing URLs", "Enter at least one URL."); return

        out_dir = Path(self.out_edit.text()).expanduser()
        if not out_dir.is_dir():
            QMessageBox.warning(self, "Bad folder", "Choose a valid directory."); return
        self._settings.setValue("last_dir", str(out_dir))

        opts = self._build_opts()
        tmpl = self.tmpl_edit.text()
        if self.prefix_chk.isChecked():
            tmpl = f"%(playlist_index)0{self.prefix_digits.value()}d - {tmpl}"
        opts["outtmpl"] = out_dir.joinpath(tmpl).as_posix()

        self.queue.enqueue(urls, opts, out_dir)
        self.urls_edit.clear(); self._refresh_queue_view()

    def _cancel_download(self):
        idx = self.queue_widget.currentRow()
        if idx >= 0: self.queue.cancel(idx)

    def _refresh_queue_view(self, *_):
        self.queue_widget.clear()
        any_running = any_done = False
        for job in self.queue.jobs():
            any_running |= job.state == "Running"
            any_done    |= job.state == "Done"
            self.queue_widget.addItem(
                QListWidgetItem(f"{job.state:9} | {', '.join(job.urls)[:60]}"))
        self.cancel_btn.setEnabled(any_running)
        self.open_folder_act.setEnabled(any_done)

    # ================================================================= yt-dlp option builder
    def _preset_fmt(self) -> str:
        idx = self.fmt_combo.currentIndex()
        if idx == 4: return self.fmt_custom.text() or "best"
        return ["bestvideo+bestaudio", "bestaudio/best",
                "bestvideo[height<=720]+bestaudio/best",
                "bestvideo[height<=1080]+bestaudio/best"][idx]

    def _build_opts(self) -> Dict[str, Any]:
        o: Dict[str, Any] = {"format": self._preset_fmt(), "merge_output_format": "mp4",
                             "quiet": True, "noprogress": True}

        if self.proxy_edit.text():   o["proxy"] = self.proxy_edit.text()
        if self.cookies_edit.text(): o["cookiefile"] = self.cookies_edit.text()
        if self.ua_edit.text():      o["user_agent"] = self.ua_edit.text()
        if self.pl_start.value():    o["playliststart"] = self.pl_start.value()
        if self.pl_end.value():      o["playlistend"] = self.pl_end.value()
        if self.chk_ignore.isChecked(): o["ignoreerrors"] = True
        if self.chk_skip.isChecked():   o["overwrites"] = False

        if self.chk_extract.isChecked():
            o.update({"extract_audio": True, "audio_format": self.audio_fmt.currentText(),
                      "merge_output_format": None})
        if self.chk_thumb.isChecked(): o["embed_thumbnail"] = True
        if self.chk_subs.isChecked():  o.update({"writesubtitles": True, "embedsubtitles": True})
        if self.chk_split.isChecked(): o["split_chapters"] = True

        if self.sb_enable.isChecked():
            buckets = {"Remove": [], "Mark": [], "Cut": []}
            for cat, cmb in self.sb_combo.items():
                act = cmb.currentText()
                if act != "None": buckets[act].append(cat)
            if buckets["Remove"]: o["sponsorblock_remove"] = buckets["Remove"]
            if buckets["Mark"]:   o["sponsorblock_mark"]   = buckets["Mark"]
            if buckets["Cut"]:    o["sponsorblock_cut"]    = buckets["Cut"]
            if self.sb_title.text().strip():
                o["sponsorblock_chapter_title"] = self.sb_title.text().strip()
            if self.sb_defaults.text().strip():
                o["sponsorblock_default_options"] = self.sb_defaults.text().strip()

        if self.extra_args.text().strip():
            o["postprocessors_args"] = [self.extra_args.text().strip()]
        return o

    # ================================================================= Tray minimise
    def closeEvent(self, ev: QCloseEvent):
        self.hide()
        self.tray_icon.showMessage("yt-dlp GUI", "Still running in system tray.")
        ev.ignore()
