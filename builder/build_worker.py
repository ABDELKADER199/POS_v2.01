"""
Background worker that executes PyInstaller (or any command-line tool)
in a separate thread with **safe cancellation** support.

Design:
    - Uses a ``_cancelled`` flag + ``process.terminate()`` instead of the
      dangerous ``QThread.terminate()`` which can corrupt state.
    - Emits progress, log, success, and failure signals so the UI can
      update without polling.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class BuildWorker(QThread):
    """Runs an external command and streams its output line-by-line."""

    log_line = pyqtSignal(str)
    progress = pyqtSignal(int)       # 0-100 estimated progress
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, command: list[str], cwd: Path) -> None:
        super().__init__()
        self.command = command
        self.cwd = cwd
        self._cancelled = False
        self._process: subprocess.Popen | None = None

    # -- public API ----------------------------------------------------------

    def cancel(self) -> None:
        """Request graceful cancellation."""
        self._cancelled = True
        if self._process is not None:
            try:
                self._process.terminate()
            except OSError:
                pass

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    # -- QThread entry point -------------------------------------------------

    def run(self) -> None:  # noqa: D401
        try:
            self._process = subprocess.Popen(
                self.command,
                cwd=str(self.cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert self._process.stdout is not None

            line_count = 0
            for line in self._process.stdout:
                if self._cancelled:
                    self._process.terminate()
                    self.failed.emit("تم إلغاء عملية الإنتاج بواسطة المستخدم.")
                    return

                stripped = line.rstrip()
                self.log_line.emit(stripped)
                line_count += 1

                # Rough progress estimation based on PyInstaller phases
                self.progress.emit(self._estimate_progress(stripped, line_count))

            code = self._process.wait()
            if self._cancelled:
                self.failed.emit("تم إلغاء عملية الإنتاج بواسطة المستخدم.")
            elif code == 0:
                self.progress.emit(100)
                self.finished_ok.emit("تم إنتاج التطبيق بنجاح.")
            else:
                self.failed.emit(f"فشل إنتاج التطبيق. كود الخروج: {code}")

        except FileNotFoundError:
            self.failed.emit("PyInstaller غير مثبت في بيئة Python الحالية.")
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self._process = None

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _estimate_progress(line: str, count: int) -> int:
        """Heuristic progress based on PyInstaller output keywords."""
        lower = line.lower()
        if "analyzing" in lower or "analysis" in lower:
            return min(20, count)
        if "processing" in lower:
            return 40
        if "building" in lower and "pyz" in lower:
            return 55
        if "building" in lower and "exe" in lower:
            return 70
        if "building" in lower and "collect" in lower:
            return 85
        if "successfully" in lower or count > 300:
            return 95
        return min(int(count * 0.3), 95)
