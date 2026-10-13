"""Generate an activation key for a customer hardware id."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.license_manager import LicenseManager


def main() -> int:
    hardware_id = " ".join(sys.argv[1:]).strip()
    if not hardware_id:
        hardware_id = input("أدخل كود الجهاز: ").strip()
    if not hardware_id:
        print("لم يتم إدخال كود الجهاز.")
        return 1
    key = LicenseManager.generate_activation_key(hardware_id)
    print(f"كود الجهاز: {hardware_id.strip().upper()}")
    print(f"مفتاح التفعيل: {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
