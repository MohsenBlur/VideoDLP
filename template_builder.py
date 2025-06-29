"""
Interactive dialog to build yt-dlp filename templates.
"""
from __future__ import annotations

from typing import List

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
)


class TemplateBuilderDialog(QDialog):
    """Drag-and-drop builder for output filename templates."""

    TOKENS = [
        ("%(playlist_index)s", "Playlist index"),
        ("%(title)s", "Title"),
        ("%(id)s", "Video ID"),
        ("%(uploader)s", "Uploader"),
        ("%(upload_date)s", "Upload date"),
        ("%(ext)s", "Extension"),
    ]

    # ──────────────────────────────── init
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filename Template Builder")
        self.resize(640, 360)

        lay = QGridLayout(self)

        # available tokens
        self.list_avail = QListWidget()
        for token, label in self.TOKENS:
            QListWidgetItem(f"{label}   ➜   {token}", self.list_avail)
        self.list_avail.itemDoubleClicked.connect(self._add_token)
        lay.addWidget(QLabel("Available placeholders:"), 0, 0)
        lay.addWidget(self.list_avail, 1, 0)

        # current template
        self.list_tpl = QListWidget()
        self.list_tpl.setDragDropMode(QListWidget.InternalMove)
        self.list_tpl.itemDoubleClicked.connect(lambda *_: self._remove_token())
        lay.addWidget(QLabel("Current template order:"), 0, 1)
        lay.addWidget(self.list_tpl, 1, 1)

        # controls
        ctrl = QHBoxLayout()
        ctrl.addWidget(QPushButton("⟶ Add", clicked=self._add_token))
        ctrl.addWidget(QPushButton("Remove ⟵", clicked=self._remove_token))
        ctrl.addWidget(QPushButton("Move ↑", clicked=lambda: self._move_sel(-1)))
        ctrl.addWidget(QPushButton("Move ↓", clicked=lambda: self._move_sel(1)))
        lay.addLayout(ctrl, 2, 0, 1, 2)

        # index padding widgets
        pad_row = QHBoxLayout()
        self.pad_label = QLabel("Zero-pad playlist index to")
        self.pad_spin = QSpinBox(minimum=1, maximum=6, value=2)
        self.pad_label.setEnabled(False); self.pad_spin.setEnabled(False)
        pad_row.addWidget(self.pad_label); pad_row.addWidget(self.pad_spin); pad_row.addStretch()
        lay.addLayout(pad_row, 3, 0, 1, 2)

        # separator
        lay.addWidget(QLabel("Separator between fields:"), 4, 0)
        self.sep_edit = QLineEdit(" - ")
        lay.addWidget(self.sep_edit, 4, 1)

        # OK/Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns, 5, 0, 1, 2)

        self.list_tpl.model().rowsInserted.connect(self._update_pad_state)
        self.list_tpl.model().rowsRemoved.connect(self._update_pad_state)

    # ─────────────────────────────── helpers
    def _add_token(self, *_):
        for item in self.list_avail.selectedItems():
            self.list_tpl.addItem(item.text())
        self._update_pad_state()

    def _remove_token(self, *_):
        for item in self.list_tpl.selectedItems():
            self.list_tpl.takeItem(self.list_tpl.row(item))
        self._update_pad_state()

    def _move_sel(self, delta: int):
        row = self.list_tpl.currentRow()
        if row < 0:
            return
        new_row = max(0, min(self.list_tpl.count() - 1, row + delta))
        if new_row == row:
            return
        item = self.list_tpl.takeItem(row)
        self.list_tpl.insertItem(new_row, item)
        self.list_tpl.setCurrentRow(new_row)

    def _update_pad_state(self):
        has_idx = any("%(playlist_index)" in self.list_tpl.item(i).text()
                      for i in range(self.list_tpl.count()))
        self.pad_label.setEnabled(has_idx)
        self.pad_spin.setEnabled(has_idx)

    # ─────────────────────────────── public
    def template_string(self) -> str:
        pieces: List[str] = []
        for i in range(self.list_tpl.count()):
            token = self.list_tpl.item(i).text().split("➜")[-1].strip()
            if token.startswith("%(playlist_index)"):
                width = self.pad_spin.value()
                token = token.replace("%(playlist_index)s", f"%(playlist_index)0{width}d")
            pieces.append(token)
        return self.sep_edit.text().join(pieces) or "%(title)s.%(ext)s"
