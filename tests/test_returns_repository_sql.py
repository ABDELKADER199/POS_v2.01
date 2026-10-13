from repositories.returns_repo import ReturnsRepository


def returns_repo_with(fetch_one=None, fetch_all=None, last_id=66):
    repo = ReturnsRepository.__new__(ReturnsRepository)
    repo.fetch_one_result = fetch_one
    repo.fetch_all_result = fetch_all or []
    repo.calls = []
    repo.db = type("FakeDB", (), {"last_insert_id": last_id, "rows_affected": 0})()

    def fake_fetch_one(query, params=None):
        repo.calls.append(("fetch_one", query, params))
        if isinstance(repo.fetch_one_result, list):
            return repo.fetch_one_result.pop(0)
        return repo.fetch_one_result

    def fake_fetch_all(query, params=None):
        repo.calls.append(("fetch_all", query, params))
        return repo.fetch_all_result

    def fake_execute(query, params=None):
        repo.calls.append(("execute", query, params))

    repo._fetch_one = fake_fetch_one
    repo._fetch_all = fake_fetch_all
    repo._execute = fake_execute
    repo._commit = lambda: repo.calls.append(("commit",))
    repo._rollback = lambda: repo.calls.append(("rollback",))
    return repo


def test_get_invoice_by_number_supports_exact_or_suffix_search():
    invoice = {"id": 1, "invoice_number": "1001"}
    repo = returns_repo_with(fetch_one=invoice)

    result = repo.get_invoice_by_number("001")

    assert result == invoice
    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "WHERE invoice_number = %s OR invoice_number LIKE %s" in query
    assert "ORDER BY id DESC LIMIT 1" in query
    assert params == ("001", "%001")


def test_get_invoice_items_includes_previously_returned_quantity_guard():
    repo = returns_repo_with(fetch_all=[])

    assert repo.get_invoice_items(10) == []

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "FROM invoice_items ii" in query
    assert "JOIN products p ON ii.product_id = p.id" in query
    assert "SELECT SUM(ri.quantity)" in query
    assert "FROM return_items ri JOIN sales_returns sr" in query
    assert "sr.original_invoice_id = ii.invoice_id" in query
    assert "LOWER(sr.status) = 'completed'" in query
    assert params == (10,)


def test_create_return_header_inserts_return_and_returns_id():
    repo = returns_repo_with(last_id=77)

    return_id = repo.create_return_header(
        return_number="RET-1",
        invoice_id=10,
        store_id=2,
        user_id=7,
        total_return=50,
        reason="خطأ بيع",
        drawer_id=4,
    )

    assert return_id == 77
    execute_call = repo.calls[0]
    assert "INSERT INTO sales_returns" in execute_call[1]
    assert "original_invoice_id" in execute_call[1]
    assert "created_by" in execute_call[1]
    assert "invoice_id, store_id, cashier_id" not in execute_call[1]
    assert execute_call[2] == ("RET-1", 10, 2, 7, 50, "خطأ بيع", 4)


def test_insert_return_item_saves_quantity_price_total_and_buy_price():
    repo = returns_repo_with()

    repo.insert_return_item(
        77,
        {
            "product_id": 10,
            "quantity": 2,
            "unit_price": 25,
            "total_price": 50,
            "buy_price": 12,
        },
    )

    execute_call = repo.calls[0]
    assert "INSERT INTO return_items" in execute_call[1]
    assert execute_call[2] == (77, 10, 2, 25, 50, 12)


def test_add_inventory_quantity_returns_stock_to_store():
    repo = returns_repo_with()

    repo.add_inventory_quantity(product_id=10, store_id=2, quantity=3)

    execute_call = repo.calls[0]
    assert "INSERT INTO product_inventory" in execute_call[1]
    assert (
        "ON DUPLICATE KEY UPDATE quantity_in_stock = quantity_in_stock + VALUES(quantity_in_stock)"
        in execute_call[1]
    )
    assert execute_call[2] == (10, 2, 3)


def test_record_cash_refund_writes_out_treasury_entry():
    repo = returns_repo_with()

    repo.record_cash_refund(
        store_id=2,
        amount=50,
        return_id=77,
        invoice_number="1001",
        return_number="RET-1",
        user_id=7,
    )

    execute_call = repo.calls[0]
    assert "INSERT INTO treasury" in execute_call[1]
    assert "user_id" in execute_call[1]
    assert "source_id" in execute_call[1]
    assert "reference_id" not in execute_call[1]
    assert "'Out'" in execute_call[1]
    assert "'Return'" in execute_call[1]
    assert execute_call[2] == (2, 7, 50, 77, "مرتجع فاتورة 1001 - RET-1")


def test_reduce_customer_balance_never_goes_below_zero():
    repo = returns_repo_with()

    repo.reduce_customer_balance(customer_id=9, amount=40)

    execute_call = repo.calls[0]
    assert "UPDATE customers" in execute_call[1]
    assert "GREATEST(0, current_balance - %s)" in execute_call[1]
    assert execute_call[2] == (40, 9)


def test_record_customer_return_ledger_reduces_credit_debt():
    repo = returns_repo_with()

    repo.record_customer_return_ledger(
        customer_id=9,
        amount=40,
        return_id=77,
        invoice_number="1001",
        user_id=7,
    )

    execute_call = repo.calls[0]
    assert "INSERT INTO financial_ledger" in execute_call[1]
    assert "'Customer'" in execute_call[1]
    assert "'Debit'" in execute_call[1]
    assert "'Return'" in execute_call[1]
    assert execute_call[2] == (
        9,
        40,
        77,
        "تخفيض مديونية العميل بسبب مرتجع فاتورة 1001",
        7,
    )


def test_returns_history_applies_store_date_and_return_number_filters():
    repo = returns_repo_with(fetch_all=[])

    result = repo.get_returns_history(
        store_id=2,
        start_date="2026-05-01",
        end_date="2026-05-31",
        return_number="RET",
    )

    assert result == []
    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "FROM sales_returns sr" in query
    assert "AND sr.store_id = %s" in query
    assert "AND DATE(sr.return_date) BETWEEN %s AND %s" in query
    assert "AND sr.return_number LIKE %s" in query
    assert "ORDER BY sr.return_date DESC LIMIT 100" in query
    assert params == (2, "2026-05-01", "2026-05-31", "%RET%")


def test_drawer_queries_for_returns_use_open_drawer_only():
    repo = returns_repo_with(fetch_one={"id": 4})

    assert repo.get_drawer_status(7) == {"id": 4}
    assert "status = 'Open'" in repo.calls[0][1]
    assert repo.calls[0][2] == (7,)

    assert repo.get_store_open_drawer(2) == {"id": 4}
    assert "dl.store_id = %s AND dl.status = 'Open'" in repo.calls[1][1]
    assert repo.calls[1][2] == (2,)
