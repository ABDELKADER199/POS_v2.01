"""Safe WhatsApp sharing helper for invoices and PDF documents."""
from __future__ import annotations

import os
import re
import struct
import subprocess
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class WhatsAppShareResult:
    opened: bool
    phone: str
    pdf_path: str
    message: str
    error: Optional[str] = None


class WhatsAppShareService:
    """Prepare a WhatsApp Desktop/Web chat without sending automatically."""

    def __init__(
        self,
        opener: Callable[[str], bool] | None = None,
        file_revealer: Callable[[str], None] | None = None,
        file_copier: Callable[[str], bool] | None = None,
        attach_automator: Callable[[], bool] | None = None,
        default_country_code: str = "20",
        auto_attach: bool = True,
        attach_delay_seconds: float = 4.0,
    ):
        self.opener = opener or self._open_url
        self.file_revealer = file_revealer or self._reveal_file
        self.file_copier = file_copier or self._copy_file_to_clipboard
        self.attach_automator = attach_automator or self._paste_clipboard_into_active_window
        self.default_country_code = default_country_code
        self.auto_attach = auto_attach
        self.attach_delay_seconds = attach_delay_seconds

    def prepare_share(self, phone: str, pdf_path: str, message: str) -> WhatsAppShareResult:
        normalized_phone = self.normalize_phone(phone)
        resolved_pdf = str(Path(pdf_path).resolve()) if pdf_path else ""
        if not normalized_phone:
            return WhatsAppShareResult(False, "", resolved_pdf, message, "رقم الهاتف غير صالح")
        if not resolved_pdf or not os.path.exists(resolved_pdf):
            return WhatsAppShareResult(False, normalized_phone, resolved_pdf, message, "ملف PDF غير موجود")

        share_text = self.build_message(message, resolved_pdf)
        opened = bool(self.opener(self.build_url(normalized_phone, message)))
        if not opened:
            opened = bool(self.opener(self.build_web_url(normalized_phone, message)))
        if opened:
            self.file_copier(resolved_pdf)
            if self.auto_attach:
                time.sleep(max(float(self.attach_delay_seconds or 0), 0))
                self.attach_automator()
        else:
            self._copy_to_clipboard(share_text)
        self.file_revealer(resolved_pdf)
        error = None if opened else "تعذر فتح واتساب تلقائيًا. افتح واتساب يدويًا والصق الرسالة المنسوخة."
        return WhatsAppShareResult(opened, normalized_phone, resolved_pdf, share_text, error)

    def prepare_text_share(self, phone: str, message: str) -> WhatsAppShareResult:
        normalized_phone = self.normalize_phone(phone)
        share_text = (message or "").strip()
        if not normalized_phone:
            return WhatsAppShareResult(False, "", "", share_text, "رقم الهاتف غير صالح")
        if not share_text:
            return WhatsAppShareResult(False, normalized_phone, "", "", "نص الرسالة فارغ")

        self._copy_to_clipboard(share_text)
        opened = bool(self.opener(self.build_url(normalized_phone, share_text)))
        if not opened:
            opened = bool(self.opener(self.build_web_url(normalized_phone, share_text)))
        error = None if opened else "تعذر فتح واتساب تلقائيًا. افتح واتساب يدويًا والصق الرسالة المنسوخة."
        return WhatsAppShareResult(opened, normalized_phone, "", share_text, error)

    def build_url(self, normalized_phone: str, message: str) -> str:
        phone = normalized_phone.lstrip("+")
        return f"whatsapp://send?phone={phone}&text={urllib.parse.quote(message or '')}"

    def build_web_url(self, normalized_phone: str, message: str) -> str:
        phone = normalized_phone.lstrip("+")
        return f"https://wa.me/{phone}?text={urllib.parse.quote(message or '')}"

    def build_message(self, message: str, pdf_path: str) -> str:
        return f"{message.strip()}\n\nملف الفاتورة:\n{pdf_path}".strip()

    def normalize_phone(self, phone: str) -> str:
        raw = str(phone or "").strip()
        if not raw:
            return ""
        has_plus = raw.startswith("+")
        digits = re.sub(r"\D+", "", raw)
        if not digits:
            return ""
        if has_plus:
            return f"+{digits}"
        if digits.startswith("00") and len(digits) > 2:
            return f"+{digits[2:]}"
        if digits.startswith("0") and len(digits) >= 10:
            return f"+{self.default_country_code}{digits[1:]}"
        if digits.startswith(self.default_country_code):
            return f"+{digits}"
        return f"+{digits}"

    @staticmethod
    def _open_url(url: str) -> bool:
        try:
            if os.name == "nt":
                os.startfile(url)  # type: ignore[attr-defined]
                return True
            return webbrowser.open(url)
        except Exception:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            phone = (query.get("phone") or [""])[0]
            text = (query.get("text") or [""])[0]
            fallback = f"https://wa.me/{phone}?text={urllib.parse.quote(text)}"
            return webbrowser.open(fallback)

    @staticmethod
    def _reveal_file(pdf_path: str) -> None:
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", f"/select,{pdf_path}"])
            else:
                webbrowser.open(Path(pdf_path).parent.as_uri())
        except Exception:
            return

    @staticmethod
    def _copy_to_clipboard(text: str) -> None:
        try:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app and app.clipboard():
                app.clipboard().setText(text)
        except Exception:
            return

    @staticmethod
    def _copy_file_to_clipboard(pdf_path: str) -> bool:
        if os.name == "nt" and WhatsAppShareService._copy_file_to_windows_clipboard(pdf_path):
            return True
        try:
            from PyQt6.QtCore import QMimeData, QUrl
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if not app or not app.clipboard():
                return False
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(str(Path(pdf_path).resolve()))])
            app.clipboard().setMimeData(mime_data)
            return True
        except Exception:
            return False

    @staticmethod
    def _copy_file_to_windows_clipboard(pdf_path: str) -> bool:
        try:
            import ctypes
            from ctypes import wintypes

            resolved_path = str(Path(pdf_path).resolve())
            if not os.path.exists(resolved_path):
                return False

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            cf_hdrop = 15
            gmem_moveable = 0x0002

            dropfiles = struct.pack(
                "<IiiII",
                20,
                0,
                0,
                0,
                1,
            )
            payload = dropfiles + resolved_path.encode("utf-16le") + b"\x00\x00\x00\x00"

            kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
            kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
            kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
            kernel32.GlobalUnlock.restype = wintypes.BOOL
            user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
            user32.SetClipboardData.restype = wintypes.HANDLE

            handle = kernel32.GlobalAlloc(gmem_moveable, len(payload))
            if not handle:
                return False
            locked = kernel32.GlobalLock(handle)
            if not locked:
                return False
            ctypes.memmove(locked, payload, len(payload))
            kernel32.GlobalUnlock(handle)

            if not user32.OpenClipboard(None):
                return False
            try:
                user32.EmptyClipboard()
                if not user32.SetClipboardData(cf_hdrop, handle):
                    return False
                handle = None
                return True
            finally:
                user32.CloseClipboard()
        except Exception:
            return False

    @staticmethod
    def _paste_clipboard_into_active_window() -> bool:
        if os.name != "nt":
            return False
        try:
            import ctypes

            WhatsAppShareService._focus_whatsapp_window()
            time.sleep(0.4)
            user32 = ctypes.windll.user32
            vk_control = 0x11
            vk_v = 0x56
            keyeventf_keyup = 0x0002
            user32.keybd_event(vk_control, 0, 0, 0)
            user32.keybd_event(vk_v, 0, 0, 0)
            user32.keybd_event(vk_v, 0, keyeventf_keyup, 0)
            user32.keybd_event(vk_control, 0, keyeventf_keyup, 0)
            return True
        except Exception:
            return False

    @staticmethod
    def _focus_whatsapp_window() -> bool:
        if os.name != "nt":
            return False
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            titles = []

            enum_windows_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def callback(hwnd, _):
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
                if "whatsapp" in title.lower() or "واتساب" in title.lower():
                    titles.append(hwnd)
                    return False
                return True

            user32.EnumWindows(enum_windows_proc(callback), 0)
            if not titles:
                return False
            hwnd = titles[0]
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False
