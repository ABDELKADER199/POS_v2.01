"""Stable local device identity helpers used by login security checks."""

from __future__ import annotations

import socket
import uuid


def get_current_device_info() -> dict:
    pc_name = socket.gethostname()
    mac = ":".join(
        f"{(uuid.getnode() >> part) & 0xff:02x}"
        for part in range(0, 8 * 6, 8)
    )
    mac = ":".join(reversed(mac.split(":")))
    return {
        "device_id": f"HW_{pc_name}_{mac.replace(':', '')}",
        "device_name": pc_name,
        "mac_address": mac,
    }
