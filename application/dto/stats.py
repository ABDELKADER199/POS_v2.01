"""Typed, presentation-neutral models for statistics and financial reports."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterator, Mapping


ZERO = Decimal("0")


def as_decimal(value: Any) -> Decimal:
    """Convert database values exactly enough for financial arithmetic."""
    if value is None or value == "":
        return ZERO
    return Decimal(str(value))


@dataclass(frozen=True)
class ExpenseLine:
    expense_type: str
    total: Decimal

    def as_dict(self) -> dict[str, Any]:
        return {"expense_type": self.expense_type, "total": self.total}


@dataclass(frozen=True)
class ProfitLossReport(Mapping[str, Any]):
    """The single calculated source of truth for P&L screen and PDF.

    Mapping compatibility is intentionally kept for existing controller clients
    while new presentation code consumes the named, typed fields.
    """

    total_sales: Decimal
    total_returns: Decimal
    supplier_promotion_claims: Decimal
    total_cogs: Decimal
    total_returned_cost: Decimal
    expenses: tuple[ExpenseLine, ...]
    invoice_count: int

    @property
    def net_sales(self) -> Decimal:
        return self.total_sales - self.total_returns

    @property
    def adjusted_net_sales(self) -> Decimal:
        return self.net_sales + self.supplier_promotion_claims

    @property
    def net_cogs(self) -> Decimal:
        return self.total_cogs - self.total_returned_cost

    @property
    def gross_profit(self) -> Decimal:
        return self.adjusted_net_sales - self.net_cogs

    @property
    def total_expenses(self) -> Decimal:
        return sum((line.total for line in self.expenses), ZERO)

    @property
    def net_profit(self) -> Decimal:
        return self.gross_profit - self.total_expenses

    @property
    def profit_margin(self) -> Decimal:
        return self.net_profit / self.adjusted_net_sales * Decimal("100") if self.adjusted_net_sales else ZERO

    @property
    def return_rate(self) -> Decimal:
        return self.total_returns / self.total_sales * Decimal("100") if self.total_sales else ZERO

    @property
    def avg_ticket(self) -> Decimal:
        return self.total_sales / self.invoice_count if self.invoice_count else ZERO

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_sales": self.total_sales,
            "total_returns": self.total_returns,
            "supplier_promotion_claims": self.supplier_promotion_claims,
            "net_sales": self.net_sales,
            "adjusted_net_sales": self.adjusted_net_sales,
            "total_cogs": self.total_cogs,
            "total_returned_cost": self.total_returned_cost,
            "net_cogs": self.net_cogs,
            "gross_profit": self.gross_profit,
            "total_expenses": self.total_expenses,
            "net_profit": self.net_profit,
            "invoice_count": self.invoice_count,
            "avg_ticket": self.avg_ticket,
            "profit_margin": self.profit_margin,
            "return_rate": self.return_rate,
        }

    def _legacy_payload(self) -> dict[str, Any]:
        return {
            "net_profit_stats": self.as_dict(),
            "expenses_breakdown": [line.as_dict() for line in self.expenses],
            "report": self,
        }

    def __getitem__(self, key: str) -> Any:
        return self._legacy_payload()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(("net_profit_stats", "expenses_breakdown", "report"))

    def __len__(self) -> int:
        return 3
