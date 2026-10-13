from models.product import Product
from repositories.accounts_repo import AccountsRepository
from repositories.inventory_repo import InventoryRepository
from repositories.product_repo import ProductRepository


def product_repo_with(rows=None, one=None, columns=None, last_id=99, affected_rows=3):
    repo = ProductRepository.__new__(ProductRepository)
    repo.fetch_all_results = list(rows or [])
    repo.fetch_one_result = one
    repo.columns = columns or set()
    repo.calls = []
    repo.db = type("FakeDB", (), {"last_insert_id": last_id, "rows_affected": affected_rows})()
    return repo


def accounts_repo_with(rows=None, one=None, last_id=77):
    repo = AccountsRepository.__new__(AccountsRepository)
    repo.fetch_all_results = list(rows or [])
    repo.fetch_one_result = one
    repo.calls = []
    repo._metadata_cache = {}
    repo.db = type("FakeDB", (), {"last_insert_id": last_id, "rows_affected": 0})()
    return repo


def inventory_repo_with(rows=None, one=None):
    repo = InventoryRepository.__new__(InventoryRepository)
    repo.fetch_all_results = list(rows or [])
    repo.fetch_one_result = one or {"cnt": 0}
    repo.calls = []
    return repo


def attach_product_repo_methods(repo):
    def fetch_all(query, params=None):
        repo.calls.append(("fetch_all", query, params))
        if query.startswith("SHOW COLUMNS"):
            return [{"Field": field} for field in repo.columns]
        if repo.fetch_all_results and isinstance(repo.fetch_all_results[0], list):
            return repo.fetch_all_results.pop(0)
        return repo.fetch_all_results

    def fetch_one(query, params=None):
        repo.calls.append(("fetch_one", query, params))
        return repo.fetch_one_result

    def execute(query, params=None):
        repo.calls.append(("execute", query, params))

    def execute_many(query, params_list):
        repo.calls.append(("execute_many", query, params_list))

    repo._fetch_all = fetch_all
    repo._fetch_one = fetch_one
    repo._execute = execute
    repo._execute_many = execute_many
    repo._commit = lambda: repo.calls.append(("commit",))
    repo._rollback = lambda: repo.calls.append(("rollback",))
    return repo


def attach_accounts_repo_methods(repo):
    def fetch_all(query, params=None):
        repo.calls.append(("fetch_all", query, params))
        if repo.fetch_all_results and isinstance(repo.fetch_all_results[0], list):
            return repo.fetch_all_results.pop(0)
        return repo.fetch_all_results

    def fetch_one(query, params=None):
        repo.calls.append(("fetch_one", query, params))
        if isinstance(repo.fetch_one_result, list):
            return repo.fetch_one_result.pop(0)
        return repo.fetch_one_result

    def execute(query, params=None):
        repo.calls.append(("execute", query, params))

    repo._fetch_all = fetch_all
    repo._fetch_one = fetch_one
    repo._execute = execute
    repo._commit = lambda: repo.calls.append(("commit",))
    repo._rollback = lambda: repo.calls.append(("rollback",))
    return repo


def attach_inventory_repo_methods(repo):
    def fetch_all(query, params=None):
        repo.calls.append(("fetch_all", query, params))
        return repo.fetch_all_results

    def fetch_one(query, params=None):
        repo.calls.append(("fetch_one", query, params))
        return repo.fetch_one_result

    repo._fetch_all = fetch_all
    repo._fetch_one = fetch_one
    return repo


def test_product_search_builds_filters_limit_and_offset():
    repo = attach_product_repo_methods(product_repo_with(rows=[]))

    result = repo.search(
        "milk",
        category_id=2,
        supplier_id=3,
        limit=25,
        offset=50,
        column_filters={
            "code": "622",
            "name": "لبن",
            "unit": "قطعة",
            "status": "ready",
            "min_sell": "10.5",
            "max_sell": "30",
        },
    )

    assert result == []
    call = repo.calls[-1]
    query = call[1]
    params = call[2]
    assert "product_name LIKE %s OR product_code LIKE %s OR barcode LIKE %s" in query
    assert "category_id = %s" in query
    assert "supplier_id = %s" in query
    assert "COALESCE(import_status, 'ready') = %s" in query
    assert "sell_price >= %s" in query
    assert "sell_price <= %s" in query
    assert query.strip().endswith("ORDER BY product_name LIMIT %s OFFSET %s")
    assert params == (
        "%milk%",
        "%milk%",
        "%milk%",
        2,
        3,
        "%622%",
        "%622%",
        "%لبن%",
        "%قطعة%",
        "ready",
        10.5,
        30.0,
        25,
        50,
    )


def test_product_count_reuses_column_filters_without_pagination():
    repo = attach_product_repo_methods(product_repo_with(one={"cnt": 12}))

    count = repo.count("p", category_id=1, supplier_id=2, column_filters={"status": "needs_pricing"})

    assert count == 12
    query = repo.calls[-1][1]
    params = repo.calls[-1][2]
    assert query.startswith("SELECT COUNT(*) as cnt FROM products")
    assert "LIMIT" not in query
    assert params == ("%p%", "%p%", "%p%", 1, 2, "needs_pricing")


def test_insert_product_includes_store_id_when_column_exists():
    repo = attach_product_repo_methods(product_repo_with(columns={"store_id"}))
    product = Product(product_code="P1", product_name="منتج", category_id=2, buy_price=5, sell_price=10)

    product_id = repo.insert_product(product, store_id=4)

    assert product_id == 99
    execute_call = [call for call in repo.calls if call[0] == "execute"][-1]
    assert "store_id" in execute_call[1]
    assert execute_call[2][3] == 4


def test_insert_product_omits_store_id_when_column_missing():
    repo = attach_product_repo_methods(product_repo_with(columns=set()))
    product = Product(product_code="P1", product_name="منتج", category_id=2, buy_price=5, sell_price=10)

    repo.insert_product(product, store_id=4)

    execute_call = [call for call in repo.calls if call[0] == "execute"][-1]
    assert "store_id" not in execute_call[1]


def test_bulk_create_chunks_products_and_inventory_with_store_id():
    rows_for_ids = [
        [{"id": 1, "product_code": "P1"}],
        [{"id": 2, "product_code": "P2"}],
    ]
    repo = attach_product_repo_methods(product_repo_with(rows=rows_for_ids, columns={"store_id"}))
    products = [
        Product(product_code="P1", product_name="منتج 1", sell_price=10),
        Product(product_code="P2", product_name="منتج 2", sell_price=20),
    ]

    created = repo.bulk_create(products, {"P1": 5, "P2": 8}, store_id=3, chunk_size=1)

    assert created == 2
    product_insert_calls = [
        call for call in repo.calls
        if call[0] == "execute_many" and "INSERT INTO products" in call[1]
    ]
    inventory_insert_calls = [
        call for call in repo.calls
        if call[0] == "execute_many" and "INSERT INTO product_inventory" in call[1]
    ]
    assert len(product_insert_calls) == 2
    assert "store_id" in product_insert_calls[0][1]
    assert product_insert_calls[0][2][0][3] == 3
    assert len(inventory_insert_calls) == 2
    assert inventory_insert_calls[0][2] == [(1, 3, 5)]
    assert inventory_insert_calls[1][2] == [(2, 3, 8)]


def test_inventory_stock_query_searches_database_and_keeps_zero_stock_branch_products():
    repo = attach_inventory_repo_methods(inventory_repo_with(rows=[]))

    assert repo.get_all_stock(store_id=3, low_stock_only=True, limit=25, offset=50, search="milk") == []
    call = repo.calls[-1]
    query = call[1]
    params = call[2]

    assert "JOIN stores s ON s.id = %s" in query
    assert "LEFT JOIN product_inventory pi ON p.id = pi.product_id AND pi.store_id = s.id" in query
    assert "COALESCE(pi.quantity_in_stock, 0) <= COALESCE(pi.minimum_quantity, 10)" in query
    assert "p.product_code LIKE %s OR p.barcode LIKE %s OR p.product_name LIKE %s" in query
    assert query.strip().endswith("ORDER BY p.product_name LIMIT %s OFFSET %s")
    assert params == (3, "%milk%", "%milk%", "%milk%", 25, 50)

    repo.fetch_one_result = {"cnt": 123}
    assert repo.count_all_stock(store_id=3, search="milk") == 123
    count_call = repo.calls[-1]
    assert "COUNT(*) AS cnt" in count_call[1]
    assert "LIMIT" not in count_call[1]
    assert count_call[2] == (3, "%milk%", "%milk%", "%milk%")


def test_accounts_get_financial_ledger_builds_search_and_type_filters():
    repo = attach_accounts_repo_methods(accounts_repo_with(rows=[]))

    result = repo.get_financial_ledger("سداد", "Customer")

    assert result == []
    query = repo.calls[-1][1]
    params = repo.calls[-1][2]
    assert "FROM financial_ledger l" in query
    assert "l.description LIKE %s" in query
    assert "l.account_type = %s" in query
    assert query.strip().endswith("ORDER BY l.transaction_date DESC LIMIT 500")
    assert params == ("%سداد%", "%سداد%", "%سداد%", "%سداد%", "Customer")


def test_accounts_insert_ledger_entry_normalizes_attachment_and_settlement_flag():
    repo = attach_accounts_repo_methods(accounts_repo_with(last_id=55))
    repo._metadata_cache["columns:financial_ledger"] = {
        "account_type",
        "account_id",
        "transaction_type",
        "amount",
        "reference_type",
        "reference_id",
        "description",
        "created_by",
        "attachment_path",
        "is_settlement",
    }

    ledger_id = repo.insert_ledger_entry(
        "Customer",
        1,
        "Debit",
        25,
        "Payment",
        "سداد",
        7,
        reference_id=3,
        attachment_path="",
        is_settlement=True,
    )

    assert ledger_id == 55
    execute_call = repo.calls[-1]
    assert "INSERT INTO financial_ledger" in execute_call[1]
    assert execute_call[2] == ("Customer", 1, "Debit", 25, "Payment", 3, "سداد", 7, None, 1)


def test_accounts_allocate_supplier_payment_distributes_oldest_invoices():
    repo = attach_accounts_repo_methods(
        accounts_repo_with(
            rows=[
                {"id": 1, "remaining_amount": 30, "paid_amount": 10},
                {"id": 2, "remaining_amount": 50, "paid_amount": 0},
            ]
        )
    )

    repo.allocate_supplier_payment(9, 60)

    updates = [call for call in repo.calls if call[0] == "execute"]
    assert updates[0][2] == (40.0, 0.0, "paid", 1)
    assert updates[1][2] == (30.0, 20.0, "partial", 2)


def test_accounts_operational_stores_exclude_general_manager_store():
    repo = attach_accounts_repo_methods(accounts_repo_with(rows=[]))

    assert repo.get_all_stores() == []

    query = repo.calls[0][1]
    assert "COALESCE(is_active, TRUE) = TRUE" in query
    assert "COALESCE(store_type, 'Branch') != 'GM'" in query


def test_accounts_financial_report_calculates_net_profit_and_cash():
    repo = attach_accounts_repo_methods(
        accounts_repo_with(
            one=[
                {"total": 1000},
                {"total": 100},
                {"total": 200},
                {"total": 50},
            ]
        )
    )

    report = repo.get_financial_report(2, "2026-05-01", "2026-05-31")

    assert report == {
        "total_sales": 1000.0,
        "total_returns": 100.0,
        "total_cogs": 0,
        "cost_of_returns": 0,
        "total_expenses": 200.0,
        "personal_expenses": 50.0,
        "net_profit": 700.0,
        "net_cash": 650.0,
    }
