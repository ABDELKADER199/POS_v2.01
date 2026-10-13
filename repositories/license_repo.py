"""Repository for hardware-bound application activation."""

from __future__ import annotations

from typing import Optional

from repositories.base_repo import BaseRepository


class LicenseRepository(BaseRepository):
    def ensure_table(self) -> None:
        self._execute("""
            CREATE TABLE IF NOT EXISTS system_license (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hardware_id VARCHAR(100) NOT NULL UNIQUE,
                activation_key VARCHAR(100) NOT NULL,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NULL DEFAULT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        self._ensure_column("activation_key", "VARCHAR(100) NOT NULL DEFAULT ''")
        self._ensure_column("activated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        self._ensure_column("expires_at", "TIMESTAMP NULL DEFAULT NULL")
        self._ensure_column("status", "VARCHAR(20) NOT NULL DEFAULT 'active'")
        self._commit()

    def _ensure_column(self, column_name: str, definition: str) -> None:
        exists = self._fetch_one("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'system_license'
              AND column_name = %s
            LIMIT 1
        """, (column_name,))
        if not exists:
            self._execute(f"ALTER TABLE system_license ADD COLUMN {column_name} {definition}")

    def get_active_license(self, hardware_id: str) -> Optional[dict]:
        return self._fetch_one("""
            SELECT *
            FROM system_license
            WHERE hardware_id = %s
              AND status = 'active'
              AND (expires_at IS NULL OR expires_at >= CURRENT_TIMESTAMP)
            LIMIT 1
        """, (hardware_id,))

    def activate(self, hardware_id: str, activation_key: str) -> None:
        self._execute("""
            INSERT INTO system_license (hardware_id, activation_key, status)
            VALUES (%s, %s, 'active')
            ON DUPLICATE KEY UPDATE
                activation_key = VALUES(activation_key),
                status = 'active',
                activated_at = CURRENT_TIMESTAMP
        """, (hardware_id, activation_key))
        self._commit()
