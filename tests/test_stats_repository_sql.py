from repositories.stats_repo import StatsRepository


def stats_repo_with(one=None, rows=None):
    repo = StatsRepository.__new__(StatsRepository)
    repo.fetch_one_result = one
    repo.fetch_all_result = rows or []
    repo.calls = []

    def fetch_one(query, params=None):
        repo.calls.append(("fetch_one", query, params))
        if isinstance(repo.fetch_one_result, list):
            return repo.fetch_one_result.pop(0)
        return repo.fetch_one_result

    def fetch_all(query, params=None):
        repo.calls.append(("fetch_all", query, params))
        return repo.fetch_all_result

    repo._fetch_one = fetch_one
    repo._fetch_all = fetch_all
    return repo


def test_sales_summary_applies_store_filter_without_fetching_profit_details():
    repo = stats_repo_with(one={"total_sales": 1000, "invoice_count": 4, "avg_ticket": 250})
    result = repo.get_sales_summary("2026-05-01", "2026-05-31", store_id=3)

    assert result == {
        "total_sales": 1000.0,
        "invoice_count": 4,
        "avg_ticket": 250.0,
    }
    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "i.status = 'Completed'" in query
    assert "AND i.store_id = %s" in query
    assert params == ("2026-05-01", "2026-05-31", 3)


def test_profit_loss_inputs_fetch_raw_sales_returns_cogs_and_expenses():
    repo = stats_repo_with(
        one=[
            {"total_sales": 1000, "invoice_count": 5},
            {"total_cogs": 400},
            {"total_returns": 100},
            {"total_returned_cost": 30},
            {"total": 0},
        ],
        rows=[{"expense_type": "Rent", "total": 120}],
    )

    result = repo.get_profit_loss_inputs("2026-05-01", "2026-05-31", store_id=2)

    assert result["total_sales"] == 1000.0
    assert result["total_cogs"] == 400.0
    assert result["total_returns"] == 100.0
    assert result["total_returned_cost"] == 30.0
    assert result["total_expenses"] == 120.0
    assert result["expenses_breakdown"] == [{"expense_type": "Rent", "total": 120}]
    assert all(call[2][-1] == 2 for call in repo.calls if call[0] == "fetch_one")
    assert "COALESCE(ii.buy_price, p.buy_price, 0)" in repo.calls[1][1]
    assert "COALESCE(ri.buy_price, p.buy_price, 0)" in repo.calls[3][1]


def test_profit_loss_inputs_use_historical_item_costs_not_current_product_costs():
    repo = stats_repo_with(
        one=[
            {"total_sales": 200, "invoice_count": 1},
            {"total_cogs": 80},
            {"total_returns": 50},
            {"total_returned_cost": 20},
            {"total": 0},
        ], rows=[]
    )

    result = repo.get_profit_loss_inputs("2026-05-01", "2026-05-31")

    cogs_query = repo.calls[1][1]
    returned_cogs_query = repo.calls[3][1]
    assert "ii.quantity * COALESCE(ii.buy_price, p.buy_price, 0)" in cogs_query
    assert "ri.quantity * COALESCE(ri.buy_price, p.buy_price, 0)" in returned_cogs_query
    assert result["total_cogs"] == 80
    assert result["total_returned_cost"] == 20


def test_total_paid_to_suppliers_uses_treasury_outflows_without_double_counting_ledgers():
    repo = stats_repo_with(one={"total": 350})

    result = repo.get_total_paid_to_suppliers(store_id=4)

    assert result == 350.0
    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "FROM treasury" in query
    assert "transaction_type = 'Out'" in query
    assert "PurchasePayment" in query
    assert "Settlement" in query
    assert "purchase_invoices" not in query
    assert "financial_ledger" not in query
    assert "AND store_id = %s" in query
    assert params == (4,)


def test_supplier_stats_uses_invoice_date_not_created_at():
    repo = stats_repo_with(rows=[])

    assert repo.get_supplier_stats("2026-05-01", "2026-05-31") == []

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "pi.created_at" not in query
    assert "DATE(pi.invoice_date) BETWEEN %s AND %s" in query
    assert "DATE(l.transaction_date) BETWEEN %s AND %s" in query
    assert params == (
        "2026-05-01",
        "2026-05-31",
        "2026-05-01",
        "2026-05-31",
        "2026-05-01",
        "2026-05-31",
        "2026-05-01",
        "2026-05-31",
        "2026-05-01",
        "2026-05-31",
    )


def test_store_queries_exclude_general_manager_store():
    repo = stats_repo_with(rows=[])

    assert repo.get_sales_by_store("2026-05-01", "2026-05-31") == []
    sales_query = repo.calls[0][1]
    assert "COALESCE(s.store_type, 'Branch') != 'GM'" in sales_query

    assert repo.get_all_stores() == []
    stores_query = repo.calls[1][1]
    assert "COALESCE(store_type, 'Branch') != 'GM'" in stores_query


def test_treasury_period_totals_applies_store_filter_and_calculates_net():
    repo = stats_repo_with(one=[{"total": 500}, {"total": 125}])

    result = repo.get_treasury_period_totals("2026-05-01", "2026-05-31", store_id=4)

    assert result == {"total_in": 500.0, "total_out": 125.0, "net": 375.0}
    in_query = repo.calls[0][1]
    out_query = repo.calls[1][1]
    assert "AND store_id = %s" in in_query
    assert "transaction_type = 'In'" in in_query
    assert "transaction_type = 'Out'" in out_query
    assert repo.calls[0][2] == ("2026-05-01", "2026-05-31", 4)
    assert repo.calls[1][2] == ("2026-05-01", "2026-05-31", 4)


def test_payment_distribution_returns_cash_and_visa_only_when_positive():
    repo = stats_repo_with(one={"cash_total": 250, "card_total": 0})

    result = repo.get_payment_method_distribution("2026-05-01", "2026-05-31", store_id=2)

    assert result == [{"payment_method": "Cash", "total": 250.0, "count": 0}]
    query = repo.calls[0][1]
    assert "SUM(cash_amount)" in query
    assert "SUM(card_amount)" in query
    assert "AND store_id = %s" in query


def test_product_sales_report_uses_store_and_date_grouping():
    repo = stats_repo_with(rows=[])

    result = repo.get_product_sales_report("2026-05-01", "2026-05-31", store_id=5)

    assert result == []
    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "JOIN stores s ON i.store_id = s.id" in query
    assert "AND i.store_id = %s" in query
    assert "GROUP BY p.id, p.product_code, p.product_name, s.id, s.store_name, DATE(i.invoice_date)" in query
    assert params == ("2026-05-01", "2026-05-31", 5)


def test_customer_retention_stats_calculates_rate_from_repeated_customers():
    repo = stats_repo_with(one={"repeat_customers": 3, "new_customers": 7, "total_customers": 10})

    result = repo.get_customer_retention_stats("2026-05-01", "2026-05-31")

    assert result == {
        "repeat_customers": 3,
        "new_customers": 7,
        "total_customers": 10,
        "retention_rate": 30.0,
    }
    query = repo.calls[0][1]
    assert "GROUP BY customer_phone" in query
    assert "order_count > 1" in query
