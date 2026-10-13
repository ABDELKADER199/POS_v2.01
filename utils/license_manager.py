"""Hardware-bound activation key generation for HyperPOS."""

from __future__ import annotations

import hashlib
import logging
import platform
import subprocess
import uuid

logger = logging.getLogger(__name__)


class LicenseManager:
    _LICENSE_SECRET = "POS_HYPERMARKET_2026_SECRET_KEY"

    @staticmethod
    def get_bios_serial() -> str:
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output(
                    ["wmic", "bios", "get", "serialnumber"],
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                ).decode(errors="ignore").split()
                if len(output) >= 2:
                    serial = output[1].strip()
                    invalid = {"0", "none", "default", "to", "be", "filled", "to be filled by o.e.m."}
                    if serial and serial.lower() not in invalid:
                        return serial

                output = subprocess.check_output(
                    ["wmic", "csproduct", "get", "uuid"],
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                ).decode(errors="ignore").split()
                if len(output) >= 2 and output[1].strip():
                    return output[1].strip()
        except Exception as exc:
            logger.debug("Could not read BIOS serial: %s", exc)
        return str(uuid.getnode())

    @classmethod
    def get_hardware_id(cls) -> str:
        raw = f"{cls.get_bios_serial()}_POS_HWID_SALT".encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest().upper()
        return f"{digest[:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"

    @classmethod
    def generate_activation_key(cls, hardware_id: str) -> str:
        normalized = (hardware_id or "").strip().upper()
        raw = f"{normalized}{cls._LICENSE_SECRET}_ACTIVATED".encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest().upper()
        return f"{digest[:4]}-{digest[8:12]}-{digest[16:20]}-{digest[24:28]}"

    @classmethod
    def verify_key(cls, hardware_id: str, key: str) -> bool:
        return (key or "").strip().upper() == cls.generate_activation_key(hardware_id)
