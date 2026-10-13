"""
Tests for builder.build_worker – safe cancellation and signal behaviour.

These tests verify the BuildWorker's contract without actually running
PyInstaller. They use harmless system commands instead.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication

from builder.build_worker import BuildWorker


# ── Ensure a QApplication exists (required for QThread signals) ────────

@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def _wait_and_process(worker: BuildWorker, timeout_ms: int = 5000) -> None:
    """Wait for the worker to finish and process pending events so signals fire."""
    worker.wait(timeout_ms)
    QCoreApplication.processEvents()


# ── Unit Tests ─────────────────────────────────────────────────────────


class TestBuildWorkerInit:
    def test_initial_state(self, tmp_path: Path):
        worker = BuildWorker(["echo", "hello"], tmp_path)
        assert not worker.is_cancelled
        assert worker._process is None

    def test_cancel_sets_flag(self, tmp_path: Path):
        worker = BuildWorker(["echo", "hello"], tmp_path)
        worker.cancel()
        assert worker.is_cancelled

    def test_cancel_without_process_is_safe(self, tmp_path: Path):
        """Cancelling before .start() must not raise."""
        worker = BuildWorker(["echo", "hello"], tmp_path)
        worker.cancel()  # should not raise


class TestBuildWorkerRun:
    """Integration-style tests using real (but safe) commands."""

    def test_successful_command(self, tmp_path: Path):
        """A trivial command should emit finished_ok."""
        worker = BuildWorker(
            [sys.executable, "-c", "print('build ok')"],
            tmp_path,
        )
        lines: list[str] = []
        worker.log_line.connect(lines.append)

        finished: list[str] = []
        worker.finished_ok.connect(finished.append)

        failed: list[str] = []
        worker.failed.connect(failed.append)

        worker.start()
        _wait_and_process(worker)

        assert len(finished) == 1, f"Expected 1 finished signal, got {len(finished)}. Failed: {failed}"
        assert len(failed) == 0
        assert any("build ok" in line for line in lines)

    def test_failing_command(self, tmp_path: Path):
        """A command that exits non-zero should emit failed."""
        worker = BuildWorker(
            [sys.executable, "-c", "import sys; sys.exit(42)"],
            tmp_path,
        )
        failed: list[str] = []
        worker.failed.connect(failed.append)

        finished: list[str] = []
        worker.finished_ok.connect(finished.append)

        worker.start()
        _wait_and_process(worker)

        assert len(failed) == 1, f"Expected 1 failed signal, got {len(failed)}. Finished: {finished}"
        assert "42" in failed[0]
        assert len(finished) == 0

    def test_cancel_during_run(self, tmp_path: Path):
        """Cancelling a running worker should emit failed (cancelled)."""
        worker = BuildWorker(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            tmp_path,
        )
        failed: list[str] = []
        worker.failed.connect(failed.append)

        worker.start()
        time.sleep(0.5)
        worker.cancel()
        _wait_and_process(worker, 10000)

        assert worker.is_cancelled
        assert len(failed) == 1
        assert "إلغاء" in failed[0]

    def test_file_not_found(self, tmp_path: Path):
        """A missing executable should emit failed with a clear message."""
        worker = BuildWorker(
            ["__nonexistent_binary_xyz__"],
            tmp_path,
        )
        failed: list[str] = []
        worker.failed.connect(failed.append)

        worker.start()
        _wait_and_process(worker)

        assert len(failed) == 1


class TestProgressEstimation:
    @pytest.mark.parametrize(
        "line,expected_min",
        [
            ("INFO: Analyzing main.py", 1),
            ("INFO: Processing module foo", 40),
            ("INFO: Building PYZ", 55),
            ("INFO: Building EXE", 70),
            ("INFO: Building COLLECT", 85),
            ("Build completed successfully", 95),
        ],
    )
    def test_phase_detection(self, line: str, expected_min: int):
        progress = BuildWorker._estimate_progress(line, 100)
        assert progress >= expected_min
