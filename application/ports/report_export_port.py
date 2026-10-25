"""Outbound report-export boundary used by statistics use cases.

Application code supplies already-authorized, presentation-neutral report data.
The adapter decides how that data becomes a PDF (or another report format).
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol


class ReportExportPort(Protocol):
    def export_dashboard(
        self,
        data: Mapping[str, Any],
        date_from: str,
        date_to: str,
        store_name: str,
        user_name: str,
    ) -> Mapping[str, Any]:
        ...

    def export_profit_loss(
        self,
        data: Mapping[str, Any],
        date_from: str,
        date_to: str,
        store_name: str,
        user_name: str,
    ) -> Mapping[str, Any]:
        ...
