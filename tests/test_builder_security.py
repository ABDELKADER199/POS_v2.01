"""
Security tests for builder.config.

Ensures that the configuration layer is hardened against:
    - Path traversal attacks (via malicious client_name / app_name).
    - Null-byte injection.
    - XSS / script injection (via sanitize_filename fallback).
    - Excessively long input (buffer overflow prevention via validation max lengths).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from builder.config import (
    MAX_CLIENT_NAME_LENGTH,
    sanitize_filename,
    validate_client_name,
)


class TestPathTraversalSecurity:
    @pytest.mark.parametrize(
        "payload,expected",
        [
            ("../../../etc/passwd", "etc_passwd"),
            ("..\\..\\Windows\\System32\\cmd.exe", "Windows_System32_cmd_exe"),
            ("/absolute/path/to/file", "absolute_path_to_file"),
            ("C:\\hidden\\path", "C_hidden_path"),
            ("~/.ssh/id_rsa", "ssh_id_rsa"),
            ("./curr/dir", "curr_dir"),
        ]
    )
    def test_directory_separators_stripped(self, payload: str, expected: str):
        """Path traversal characters like dot and slashes/backslashes must be removed/replaced."""
        assert sanitize_filename(payload) == expected

    @pytest.mark.parametrize(
        "payload,expected",
        [
            ("my_client\0_secret", "my_client_secret"),
            ("foo\x00bar", "foo_bar"),
            ("test\n\rdir", "test_dir"),
        ]
    )
    def test_null_bytes_and_control_chars_stripped(self, payload: str, expected: str):
        """Null bytes and newlines must be stripped out so they cannot confuse the OS."""
        assert sanitize_filename(payload) == expected


class TestSpecialCharactersSecurity:
    @pytest.mark.parametrize(
        "payload,expected",
        [
            ("<script>alert(1)</script>", "script_alert_1_script"),
            ("' OR 1=1 --", "OR_1_1_--"),
            ("name&echo hack", "name_echo_hack"),
            ("$(rm -rf /)", "rm_-rf"),
            ("name|format C:", "name_format_C"),
            ("client>output.txt", "client_output_txt"),
        ]
    )
    def test_injection_characters_replaced(self, payload: str, expected: str):
        """Characters used in XSS, SQLi, and shell injection must be replaced."""
        assert sanitize_filename(payload) == expected

    def test_arabic_characters_preserved(self):
        """Legitimate Arabic characters must not be sanitized as malicious."""
        arabic_name = "سوبرماركت الأمل - فرع 1"
        assert sanitize_filename(arabic_name) == "سوبرماركت_الأمل_-_فرع_1"

    def test_english_alphanumeric_preserved(self):
        valid_name = "HyperPOS_Client-1"
        assert sanitize_filename(valid_name) == "HyperPOS_Client-1"


class TestLengthAndResourceExhaustion:
    def test_sanitizer_empty_and_whitespace(self):
        assert sanitize_filename("") == "app"
        assert sanitize_filename("       ") == "app"
        assert sanitize_filename(None) == "app"

    def test_sanitizer_extremely_large_input(self):
        """Should not crash on extremely large input."""
        large_input = "a" * 10000 + "!" * 10000 + "ب" * 10000
        # Should finish quickly and properly sanitize
        result = sanitize_filename(large_input)
        assert len(result) == 20001  # 10000 'a' + 1 '_' + 10000 'ب'
        assert "!" not in result

    def test_validate_client_name_max_length_enforced(self):
        """The validation layer should outright reject inputs that are too long."""
        malicious_long_name = "A" * (MAX_CLIENT_NAME_LENGTH + 1)
        ok, msg = validate_client_name(malicious_long_name)
        assert not ok
        assert "طويل" in msg

    def test_validate_client_name_max_length_allowed(self):
        borderline_name = "A" * MAX_CLIENT_NAME_LENGTH
        ok, msg = validate_client_name(borderline_name)
        assert ok
