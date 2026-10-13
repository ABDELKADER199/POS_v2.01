from repositories.purchases_repo import PurchasesRepository


def purchases_repo_with(fetch_one=None, fetch_all=None, last_id=42):
    repo = PurchasesRepository.__new__(PurchasesRepository)
    repo.fetch_one_result = fetch_one
    repo.fetch_all_result = fetch_all or []
    repo.calls = []
    repo._metadata_cache = {"columns:purchase_return_items": {"purchase_return_id", "quantity"}}
    repo.db = type("FakeDB", (), {"last_insert_id": last_id, "rows_affected": 0})()

    def fake_fetch_one(query, params=None):
        repo.calls.append(("fetch_one", query, params))
        if isinstance(repo.fetch_one_result, list):
            return repo.fetch_one_result.pop(0)
        return repo.fetch_one_result

    def fake_fetch_all(query, params=None):
        repo.calls.append(("fetch_all", query, params))
        if (
            isinstance(repo.fetch_all_result, list)
            and repo.fetch_all_result
            and isinstance(repo.fetch_all_result[0], list)
        ):
            return repo.fetch_all_result.pop(0)
        return repo.fetch_all_result

    def fake_execute(query, params=None):
        repo.calls.append(("execute", query, params))

    repo._fetch_one = fake_fetch_one
    repo._fetch_all = fake_fetch_all
    repo._execute = fake_execute
    repo._commit = lambda: repo.calls.append(("commit",))
    repo._rollback = lambda: repo.calls.append(("rollback",))
    return repo


def test_get_all_stores_returns_active_stores_ordered_by_id():
    repo = purchases_repo_with(fetch_all=[{"id": 1, "store_name": "Main"}])

    assert repo.get_all_stores() == [{"id": 1, "store_name": "Main"}]
    call = repo.calls[0]
    assert call[0] == "fetch_all"
    assert "FROM stores" in call[1]
    assert "COALESCE(is_active, TRUE) = TRUE" in call[1]
    assert "COALESCE(store_type, 'Branch') != 'GM'" in call[1]
    assert "ORDER BY id" in call[1]


def test_create_purchase_invoice_header_inserts_then_assigns_final_number():
    repo = purchases_repo_with(last_id=123)

    invoice = repo.create_purchase_invoice_header(
        supplier_id=5,
        user_id=7,
        ref_number="REF-1",
        subtotal=100,
        discount=10,
        tax=5,
        total=95,
        paid=40,
        remaining=55,
        payment_method="Cash",
        payment_status="partial",
    )

    assert invoice == {"id": 123, "invoice_number": "PUR-000123"}
    insert_call = repo.calls[0]
    update_call = repo.calls[1]
    assert "INSERT INTO purchase_invoices" in insert_call[1]
    assert insert_call[2][0].startswith("TMP-")
    assert insert_call[2][1:] == (
        5,
        7,
        "REF-1",
        100,
        10,
        5,
        95,
        40,
        55,
        "Cash",
        "partial",
    )
    assert update_call == (
        "execute",
        "UPDATE purchase_invoices SET invoice_number = %s WHERE id = %s",
        ("PUR-000123", 123),
    )


def test_insert_purchase_item_calculates_total_cost_and_null_expiry():
    repo = purchases_repo_with()

    repo.insert_purchase_item(
        invoice_id=10, product_id=20, quantity=3, unit_cost=12.5, expiry_date=""
    )

    execute_call = repo.calls[0]
    assert "INSERT INTO purchase_items" in execute_call[1]
    assert execute_call[2] == (10, 20, 3, 12.5, 37.5, None)


def test_add_inventory_quantity_updates_existing_row_or_inserts_new_row():
    repo = purchases_repo_with(fetch_one=[{"id": 1}, None])

    repo.add_inventory_quantity(product_id=10, store_id=2, quantity=5)
    repo.add_inventory_quantity(product_id=11, store_id=2, quantity=7)

    update_call = repo.calls[1]
    insert_call = repo.calls[3]
    assert "UPDATE product_inventory" in update_call[1]
    assert update_call[2] == (5, 10, 2)
    assert "INSERT INTO product_inventory" in insert_call[1]
    assert insert_call[2] == (11, 2, 7)


def test_update_product_after_purchase_uses_optional_product_columns():
    repo = purchases_repo_with()
    repo._metadata_cache["columns:products"] = {
        "supplier_id",
        "last_supplier",
        "last_purchase_date",
    }

    repo.update_product_after_purchase(
        product_id=10,
        buy_price=8.5,
        sell_price=12,
        supplier_id=3,
        supplier_name="مورد",
    )

    execute_call = repo.calls[0]
    query = execute_call[1]
    params = execute_call[2]
    assert "buy_price = %s" in query
    assert "sell_price = %s" in query
    assert "supplier_id = %s" in query
    assert "last_supplier = %s" in query
    assert "last_purchase_date = CURDATE()" in query
    assert params == (8.5, 12, 3, "مورد", 10)


def test_update_product_after_purchase_skips_sell_price_when_not_positive():
    repo = purchases_repo_with()
    repo._metadata_cache["columns:products"] = {"supplier_id"}

    repo.update_product_after_purchase(
        10, buy_price=8, sell_price=0, supplier_id=3, supplier_name="مورد"
    )

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "sell_price = %s" not in query
    assert params == (8, 3, 10)


def test_update_purchase_invoice_payment_state_builds_update_query():
    repo = purchases_repo_with()

    repo.update_purchase_invoice_payment_state(
        9,
        paid_amount=70,
        remaining_amount=30,
        payment_status="partial",
        payment_method="Visa",
    )

    execute_call = repo.calls[0]
    assert "UPDATE purchase_invoices" in execute_call[1]
    assert execute_call[2] == (70, 30, "partial", "Visa", 9)


def test_get_purchase_invoice_for_payment_includes_payment_method():
    repo = purchases_repo_with(fetch_one={"id": 9, "payment_method": "Credit"})

    assert repo.get_purchase_invoice_for_payment(9) == {
        "id": 9,
        "payment_method": "Credit",
    }
    assert "payment_method" in repo.calls[0][1]


def test_reconcile_purchase_return_credits_recalculates_remaining_amount():
    repo = purchases_repo_with()

    repo.reconcile_purchase_return_credits(9)

    execute_call = repo.calls[0]
    assert "UPDATE purchase_invoices pi" in execute_call[1]
    assert "purchase_returns" in execute_call[1]
    assert "COALESCE(settlement_method, 'credit') = 'credit'" in execute_call[1]
    assert "pi.remaining_amount = GREATEST" in execute_call[1]
    assert "WHERE pi.id = %s" in execute_call[1]
    assert execute_call[2] == (9,)


def test_allocate_supplier_payment_distributes_amount_over_oldest_open_invoices():
    repo = purchases_repo_with(
        fetch_all=[
            {"id": 1, "remaining_amount": 30, "paid_amount": 10},
            {"id": 2, "remaining_amount": 50, "paid_amount": 0},
            {"id": 3, "remaining_amount": 20, "paid_amount": 5},
        ]
    )

    repo.allocate_supplier_payment(supplier_id=4, amount=65)

    updates = [call for call in repo.calls if call[0] == "execute"]
    assert updates[0][2] == (40.0, 0.0, "paid", 1)
    assert updates[1][2] == (35.0, 15.0, "partial", 2)
    assert len(updates) == 2


def test_reconcile_supplier_open_invoices_allocates_difference_and_commits():
    repo = purchases_repo_with(
        fetch_one=[{"id": 4, "current_balance": 40}, {"invoice_balance": 100}]
    )

    difference = repo.reconcile_supplier_open_invoices(4)

    assert difference == 60.0
    assert any(call[0] == "commit" for call in repo.calls)
    assert any(
        call[0] == "fetch_all" and "purchase_invoices" in call[1] for call in repo.calls
    )


def test_reconcile_supplier_open_invoices_noops_when_supplier_missing_or_no_difference():
    repo = purchases_repo_with(fetch_one=None)

    assert repo.reconcile_supplier_open_invoices(4) == 0.0
    assert not any(call[0] == "commit" for call in repo.calls)

    repo = purchases_repo_with(
        fetch_one=[{"id": 4, "current_balance": 100}, {"invoice_balance": 80}]
    )
    assert repo.reconcile_supplier_open_invoices(4) == 0.0
    assert not any(call[0] == "commit" for call in repo.calls)


def test_sync_supplier_balance_from_open_invoices_updates_supplier_balance():
    repo = purchases_repo_with()

    repo.sync_supplier_balance_from_open_invoices(4)

    call = repo.calls[0]
    assert call[0] == "execute"
    assert "UPDATE suppliers s" in call[1]
    assert "SUM(remaining_amount)" in call[1]
    assert "SET s.current_balance = COALESCE(pi.open_balance, 0)" in call[1]
    assert "WHERE s.id = %s" in call[1]
    assert call[2] == (4,)


def test_record_supplier_purchase_debt_respects_financial_ledger_table():
    repo = purchases_repo_with(fetch_one={"current_balance": 20})
    repo._metadata_cache["tables"] = set()

    repo.record_supplier_purchase_debt(1, 2, 7, 9, 50, "مديونية")
    assert not any(call[0] == "execute" for call in repo.calls)

    repo._metadata_cache["tables"] = {"financial_ledger"}
    repo.record_supplier_purchase_debt(1, 2, 7, 9, 50, "مديونية")
    execute_call = repo.calls[-1]
    assert "INSERT INTO financial_ledger" in execute_call[1]
    assert execute_call[2] == (2, 1, "مديونية", 50, 9, 20, 70, 7)


def test_record_supplier_payment_writes_ledger_and_treasury_when_tables_exist():
    repo = purchases_repo_with()
    repo._metadata_cache["tables"] = {"financial_ledger", "treasury"}
    repo._metadata_cache["columns:treasury"] = {
        "store_id",
        "user_id",
        "transaction_type",
        "amount",
        "description",
        "source_type",
        "source_id",
    }

    repo.record_supplier_payment(
        supplier_id=1,
        store_id=2,
        user_id=7,
        invoice_id=9,
        amount=35,
        payment_method="Cash",
        description="سداد",
        record_ledger=True,
    )

    ledger_call, treasury_call = [call for call in repo.calls if call[0] == "execute"]
    assert "INSERT INTO financial_ledger" in ledger_call[1]
    assert ledger_call[2] == (1, 35, 9, "سداد", 7)
    assert "INSERT INTO treasury" in treasury_call[1]
    assert "transaction_type" in treasury_call[1]
    assert "source_id" in treasury_call[1]
    assert treasury_call[2] == (2, 7, "Out", 35, "سداد - Cash", "PurchasePayment", 9)


def test_record_supplier_payment_can_skip_ledger_and_noops_for_zero_amount():
    repo = purchases_repo_with()
    repo._metadata_cache["tables"] = {"financial_ledger", "treasury"}

    repo.record_supplier_payment(1, 2, 7, 9, 0, "Cash", "سداد", True)
    assert repo.calls == []

    repo._metadata_cache["columns:treasury"] = {
        "store_id",
        "user_id",
        "transaction_type",
        "amount",
        "description",
        "source_type",
        "source_id",
    }
    repo.record_supplier_payment(1, 2, 7, 9, 35, "Cash", "سداد", False)
    execute_calls = [call for call in repo.calls if call[0] == "execute"]
    assert len(execute_calls) == 1
    assert "INSERT INTO treasury" in execute_calls[0][1]


def test_record_supplier_payment_supports_legacy_treasury_columns():
    repo = purchases_repo_with()
    repo._metadata_cache["tables"] = {"treasury"}
    repo._metadata_cache["columns:treasury"] = {
        "store_id",
        "amount",
        "reference_id",
        "description",
        "created_by",
    }

    repo.record_supplier_payment(1, 2, 7, 9, 35, "Cash", "سداد", False)

    execute_call = next(call for call in repo.calls if call[0] == "execute")
    assert "reference_id" in execute_call[1]
    assert execute_call[2] == (2, 35, "سداد - Cash", 7, 9)


def test_supplier_balance_queries_and_purchase_history_sql():
    repo = purchases_repo_with(fetch_all=[])

    assert repo.get_purchase_history() == []
    query = repo.calls[0][1]
    assert "pi.invoice_date as created_at" in query
    assert "ORDER BY pi.invoice_date DESC" in query
    assert repo.calls[0][2] == (100, 0)

    repo.increase_supplier_balance(1, 20)
    repo.decrease_supplier_balance(1, 10)
    assert repo.calls[-2][2] == (20, 1)
    assert repo.calls[-1][2] == (10, 1)


def test_update_and_soft_delete_supplier_queries_commit():
    repo = purchases_repo_with()

    assert repo.update_supplier(1, "مورد", "010", "عنوان", "TX") is True
    assert repo.soft_delete_supplier(1) is True

    execute_calls = [call for call in repo.calls if call[0] == "execute"]
    assert "UPDATE suppliers" in execute_calls[0][1]
    assert execute_calls[0][2] == ("مورد", "010", "عنوان", "TX", 1)
    assert "SET is_active = FALSE" in execute_calls[1][1]
    assert execute_calls[1][2] == (1,)
    assert len([call for call in repo.calls if call[0] == "commit"]) == 2


def test_purchase_return_header_and_items_sql():
    repo = purchases_repo_with(last_id=77)
    repo._metadata_cache["columns:purchase_return_items"] = {
        "return_id",
        "product_id",
        "quantity",
        "unit_cost",
        "total_cost",
    }

    result = repo.create_purchase_return_header(
        purchase_invoice_id=9,
        supplier_id=1,
        store_id=2,
        user_id=3,
        total_amount=120,
        settlement_method="credit",
        reason="تالف",
    )
    repo.insert_purchase_return_item(77, 10, 2, 30)

    assert result == {"id": 77, "return_number": "PR-000077"}
    assert "INSERT INTO purchase_returns" in repo.calls[0][1]
    assert repo.calls[0][2][1:] == (9, 1, 2, 3, 120, "credit", "تالف")
    assert repo.calls[1][2] == ("PR-000077", 77)
    assert "INSERT INTO purchase_return_items" in repo.calls[2][1]
    assert "return_id" in repo.calls[2][1]
    assert repo.calls[2][2] == (77, 10, 2, 30, 60)


def test_purchase_invoice_details_loads_invoice_and_items():
    repo = purchases_repo_with(
        fetch_one={"id": 9, "invoice_number": "PUR-9"},
        fetch_all=[
            [
                {
                    "product_id": 10,
                    "product_name": "منتج",
                    "quantity": 5,
                    "returned_quantity": 1,
                }
            ]
        ],
    )

    result = repo.get_purchase_invoice_details("PUR-9")

    assert result["items"] == [
        {
            "product_id": 10,
            "product_name": "منتج",
            "quantity": 5,
            "returned_quantity": 1.0,
            "remaining_quantity": 0,
            "returnable_quantity": 0,
        }
    ]
    assert "FROM purchase_invoices pi" in repo.calls[0][1]
    assert "FROM purchase_items pitems" in repo.calls[1][1]
    assert "LEFT JOIN products" in repo.calls[1][1]
    assert "products.product_name AS product_name" in repo.calls[1][1]
    assert repo.calls[0][2] == ("PUR-9", "PUR-9", "%PUR-9%")


def test_purchase_return_quantity_and_inventory_queries():
    repo = purchases_repo_with(fetch_one=[{"remaining_qty": 3}, {"qty": 8}])
    repo._metadata_cache["columns:purchase_return_items"] = {
        "return_id",
        "product_id",
        "quantity",
    }

    assert repo.get_purchase_item_remaining_quantity(9, 10) == 3
    assert repo.get_inventory_quantity(10, 2) == 8
    assert "purchase_return_items" in repo.calls[0][1]
    assert "pri.return_id" in repo.calls[0][1]
    assert "product_inventory" in repo.calls[1][1]


def test_purchase_return_items_supports_legacy_purchase_return_id_column():
    repo = purchases_repo_with(fetch_one={"remaining_qty": 3})
    repo._metadata_cache["columns:purchase_return_items"] = {
        "purchase_return_id",
        "product_id",
        "quantity",
    }

    repo.insert_purchase_return_item(77, 10, 2, 30)
    assert "purchase_return_id" in repo.calls[0][1]

    assert repo.get_purchase_item_remaining_quantity(9, 10) == 3
    assert "pri.purchase_return_id" in repo.calls[1][1]


def test_decrease_inventory_quantity_builds_update_query():
    repo = purchases_repo_with()

    repo.decrease_inventory_quantity(10, 2, 3)

    assert "UPDATE product_inventory" in repo.calls[0][1]
    assert repo.calls[0][2] == (3, 10, 2)


def test_purchase_return_accounting_writes_ledger_and_treasury():
    repo = purchases_repo_with()
    repo._metadata_cache["tables"] = {"financial_ledger", "treasury"}
    repo._metadata_cache["columns:treasury"] = {
        "store_id",
        "user_id",
        "transaction_type",
        "amount",
        "description",
        "source_type",
        "source_id",
    }

    repo.record_supplier_purchase_return_credit(1, 2, 7, 77, 50, "مرتجع")
    repo.record_purchase_return_cash_refund(1, 2, 7, 77, 60, "استرداد")

    execute_calls = [call for call in repo.calls if call[0] == "execute"]
    assert "INSERT INTO financial_ledger" in execute_calls[0][1]
    assert execute_calls[0][2] == (1, 2, 50, 0.0, 50.0, 77, "مرتجع", 7)
    assert "'Return'" in execute_calls[0][1]
    assert "INSERT INTO financial_ledger" in execute_calls[1][1]
    assert execute_calls[1][2] == (1, 60, 77, "استرداد", 7)
    assert "'Return'" in execute_calls[1][1]
    assert "INSERT INTO treasury" in execute_calls[2][1]
    assert execute_calls[2][2] == (2, 7, "In", 60, "استرداد", "PurchaseReturn", 77)
