"""
HyperPOS Developer Builder – entry point.

This script is the thin entry-point that launches the developer GUI.
All logic lives inside the ``builder`` package:

    builder/
        config.py          – labels, presets, validation rules
        build_worker.py    – background thread for PyInstaller
        builder_window.py  – DeveloperBuilderWindow (Qt)
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from builder.builder_window import DeveloperBuilderWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    window = DeveloperBuilderWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
