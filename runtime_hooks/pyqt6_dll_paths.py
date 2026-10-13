import os
import sys


if sys.platform.startswith("win") and hasattr(sys, "_MEIPASS"):
    for dll_directory in (
        sys._MEIPASS,
        os.path.join(sys._MEIPASS, "PyQt6", "Qt6", "bin"),
    ):
        if os.path.isdir(dll_directory):
            os.add_dll_directory(dll_directory)
