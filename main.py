"""
Entry-point for the yt-dlp GUI.
"""
import sys
from PySide6.QtWidgets import QApplication
from gui import MainWindow


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
