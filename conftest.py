import os
import sys

if sys.platform.startswith("win"):
    try:
        import PyQt6
        bin_dir = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "bin")
        if os.path.isdir(bin_dir):
            os.add_dll_directory(bin_dir)
    except Exception:
        pass
