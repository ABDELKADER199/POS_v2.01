"""Central logging setup for HyperPOS.

Creates persistent log files and captures unhandled Python, thread, and Qt
errors so field installations have a reliable diagnostic trail.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType


APP_LOG_NAME = "app.log"
ERROR_LOG_NAME = "error.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


def setup_application_logging(base_dir: str | os.PathLike[str] | None = None) -> Path:
    """Configure root logging and return the error log path."""

    log_dir = _resolve_log_dir(base_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT)

    app_handler = RotatingFileHandler(
        log_dir / APP_LOG_NAME,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        log_dir / ERROR_LOG_NAME,
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    logging.captureWarnings(True)

    logging.getLogger(__name__).info("Logging initialized. Logs directory: %s", log_dir)
    return log_dir / ERROR_LOG_NAME


def install_exception_hooks(logger: logging.Logger | None = None) -> None:
    """Log unhandled main-thread and worker-thread exceptions."""

    active_logger = logger or logging.getLogger(__name__)

    def handle_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        active_logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

    def handle_thread_exception(args: threading.ExceptHookArgs) -> None:
        active_logger.critical(
            "Unhandled thread exception: %s",
            getattr(args.thread, "name", "unknown"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception


def install_qt_message_handler(logger: logging.Logger | None = None) -> None:
    """Route Qt warnings and critical messages to the Python log files."""

    try:
        from PyQt6.QtCore import QtMsgType, qInstallMessageHandler
    except Exception:
        return

    active_logger = logger or logging.getLogger("qt")

    def qt_message_handler(mode, context, message: str) -> None:
        source = getattr(context, "file", "") or "Qt"
        line = getattr(context, "line", 0)
        formatted = f"{source}:{line} - {message}"
        if mode == QtMsgType.QtDebugMsg:
            active_logger.debug(formatted)
        elif mode == QtMsgType.QtInfoMsg:
            active_logger.info(formatted)
        elif mode == QtMsgType.QtWarningMsg:
            active_logger.warning(formatted)
        elif mode == QtMsgType.QtCriticalMsg:
            active_logger.error(formatted)
        elif mode == QtMsgType.QtFatalMsg:
            active_logger.critical(formatted)
        else:
            active_logger.info(formatted)

    qInstallMessageHandler(qt_message_handler)


def _resolve_log_dir(base_dir: str | os.PathLike[str] | None = None) -> Path:
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
    elif base_dir:
        root = Path(base_dir).resolve()
    else:
        root = Path.cwd().resolve()
    return root / "logs"
