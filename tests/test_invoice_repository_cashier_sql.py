import pytest

from repositories.invoice_repo import InvoiceRepository


def invoice_repo_with(fetch_one=None, fetch_all=None, columns=None, last_id=100):
    repo = InvoiceRepository.__new__(InvoiceRepository)
    repo.fetch_one_result = fetch_one
    repo.fetch_all_result = fetch_all or []
    repo.columns = columns or {}
    repo.calls = []
    repo._metadata_cache = {}
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
    repo._columns = lambda table_name: repo.columns.get(table_name, set())
    return repo


def test_insert_invoice_header_saves_sale_header_with_payment_split():
    repo = invoice_repo_with(last_id=55)

    invoice_id = repo.insert_invoice_header(
        invoice_number="1001",
        store_id=2,
        cashier_id=7,
        customer_id=9,
        customer_name="عميل",
        customer_phone="010",
        customer_address="عنوان",
        drawer_id=3,
        payment_method="Mixed",
        cash_amount=60,
        card_amount=40,
        total_amount=100,
        paid_amount=100,
        remaining_amount=0,
        subtotal_amount=90,
        tax_amount=10,
    )

    assert invoice_id == 55
    execute_call = repo.calls[0]
    assert "INSERT INTO invoices" in execute_call[1]
    assert execute_call[2] == (
        "1001",
        2,
        7,
        9,
        "عميل",
        "010",
        "عنوان",
        3,
        "Mixed",
        60,
        40,
        100,
        100,
        0,
        90,
        10,
    )


def test_insert_sale_item_includes_optional_cost_and_tax_columns():
    repo = invoice_repo_with(
        columns={"invoice_items": {"buy_price", "item_subtotal", "item_tax"}}
    )

    repo.insert_sale_item(
        invoice_id=1,
        product_id=10,
        quantity=2,
        unit_price=25,
        discount=3,
        total_price=47,
        buy_price=15,
        item_subtotal=42,
        item_tax=5,
    )

    execute_call = repo.calls[0]
    assert "buy_price" in execute_call[1]
    assert "item_subtotal" in execute_call[1]
    assert "item_tax" in execute_call[1]
    assert execute_call[2] == (1, 10, 2, 25, 3, 47, 15, 42, 5)


def test_decrease_product_inventory_builds_stock_deduction_query():
    repo = invoice_repo_with()

    repo.decrease_product_inventory(product_id=10, store_id=2, quantity=3)

    execute_call = repo.calls[0]
    assert "UPDATE product_inventory" in execute_call[1]
    assert "quantity_in_stock = quantity_in_stock - %s" in execute_call[1]
    assert execute_call[2] == (3, 10, 2)


def test_apply_sale_financial_effects_records_cash_and_credit_customer_balance():
    repo = invoice_repo_with()

    repo.apply_sale_financial_effects(
        invoice_id=5,
        invoice_number="1001",
        store_id=2,
        cashier_id=7,
        customer_id=9,
        cash_amount=60,
        remaining_amount=40,
    )

    calls = [call for call in repo.calls if call[0] == "execute"]
    assert "INSERT INTO treasury" in calls[0][1]
    assert calls[0][2] == (2, 60, 5, "مبيعات نقدية: فاتورة رقم 1001", 7)
    assert "UPDATE customers SET current_balance" in calls[1][1]
    assert calls[1][2] == (40, 9)
    assert "INSERT INTO financial_ledger" in calls[2][1]
    assert calls[2][2] == (9, 40, 5, "مديونية فاتورة رقم 1001", 7)


def test_get_or_create_customer_updates_existing_customer_by_phone():
    repo = invoice_repo_with(fetch_one={"id": 12})

    customer_id = repo.get_or_create_customer(" عميل ", " 010 ", " عنوان ")

    assert customer_id == 12
    assert repo.calls[0] == (
        "fetch_one",
        "SELECT id FROM customers WHERE phone = %s LIMIT 1",
        ("010",),
    )
    update_call = repo.calls[1]
    assert (
        "UPDATE customers SET name = %s, address = %s WHERE id = %s" == update_call[1]
    )
    assert update_call[2] == ("عميل", "عنوان", 12)


def test_get_or_create_customer_inserts_new_customer_or_returns_none_for_empty_data():
    repo = invoice_repo_with(fetch_one=None, last_id=22)

    assert repo.get_or_create_customer("", "", "") is None
    customer_id = repo.get_or_create_customer("", "010", "")

    assert customer_id == 22
    insert_call = repo.calls[-1]
    assert "INSERT INTO customers" in insert_call[1]
    assert insert_call[2] == ("عميل نقدي", "010", None)


def test_customer_lookup_and_credit_limit_guard():
    repo = invoice_repo_with(
        fetch_one={"name": "عميل", "current_balance": 80, "credit_limit": 100}
    )

    ok, message = repo.check_credit_limit(1, 30)

    assert ok is False
    assert "عميل" in message
    assert repo.calls[0][2] == (1,)

    repo = invoice_repo_with(
        fetch_one={"name": "عميل", "current_balance": 80, "credit_limit": 0}
    )
    assert repo.check_credit_limit(1, 100) == (True, "")

    repo = invoice_repo_with(fetch_one=None)
    assert repo.get_customer_by_phone("") is None
    assert repo.get_customer_by_phone("010") is None


def test_held_invoice_header_items_search_and_delete_sql():
    repo = invoice_repo_with(fetch_all=[])

    repo.insert_held_invoice_header("TMP-1", 2, 7, "عميل", "010", "عنوان", 150)
    repo.insert_held_invoice_item(5, 10, 2, 25, 0, 50)
    repo.delete_held_invoice_record(5)
    assert "customer_address" in repo.calls[0][1]
    assert repo.get_held_invoices(2, "010") == []

    assert "INSERT INTO temporary_invoices" in repo.calls[0][1]
    assert repo.calls[0][2] == ("TMP-1", 2, 7, "عميل", "010", "عنوان", 150, 7)
    assert "INSERT INTO temporary_invoice_items" in repo.calls[1][1]
    assert repo.calls[1][2] == (5, 10, 2, 25, 0, 50)
    assert repo.calls[2] == (
        "execute",
        "DELETE FROM temporary_invoices WHERE id = %s",
        (5,),
    )
    held_query = repo.calls[3][1]
    held_params = repo.calls[3][2]
    assert "ti.temp_invoice_code LIKE %s" in held_query
    assert held_params == (2, "%010%", "%010%", "%010%")


def test_invoice_history_queries_apply_store_search_and_dates():
    repo = invoice_repo_with(fetch_all=[])

    assert repo.get_recent(store_id=2, limit=5) == []
    assert repo.get_completed_invoices(2, "010", "2026-05-01", "2026-05-31") == []

    recent_query, recent_params = repo.calls[0][1], repo.calls[0][2]
    assert "AND store_id = %s" in recent_query
    assert recent_params == (2, 5)

    completed_query, completed_params = repo.calls[1][1], repo.calls[1][2]
    assert "i.status = 'Completed'" in completed_query
    assert "i.store_id = %s" in completed_query
    assert "i.invoice_number LIKE %s" in completed_query
    assert "DATE(i.invoice_date) BETWEEN %s AND %s" in completed_query
    assert completed_params == (
        2,
        "%010%",
        "%010%",
        "%010%",
        "2026-05-01",
        "2026-05-31",
    )


def test_open_orders_and_order_items_queries_for_call_center_cashier_flow():
    repo = invoice_repo_with(fetch_all=[])

    assert repo.get_open_orders(2, "CC") == []
    assert repo.get_order_items(9) == []
    repo.update_order_status_record(9, "Delivered")

    orders_query, orders_params = repo.calls[0][1], repo.calls[0][2]
    assert "COALESCE(o.destination_store_id, o.source_store_id) = %s" in orders_query
    assert "o.status IN ('Pending', 'Confirmed', 'Prepared')" in orders_query
    assert orders_params == (2, "%CC%", "%CC%", "%CC%")
    assert "JOIN products p ON oi.product_id = p.id" in repo.calls[1][1]
    assert repo.calls[2] == (
        "execute",
        "UPDATE orders SET status = %s WHERE id = %s",
        ("Delivered", 9),
    )


def test_validate_sale_stock_raises_when_quantity_invalid_or_stock_insufficient():
    repo = invoice_repo_with(fetch_one={"qty": 1})

    with pytest.raises(ValueError):
        repo.validate_sale_stock([{"product_id": 10, "quantity": 0}], store_id=2)

    with pytest.raises(ValueError):
        repo.validate_sale_stock(
            [{"product_id": 10, "quantity": 2, "product_name": "منتج"}], store_id=2
        )


def test_calculate_promotions_applies_product_category_and_buy_x_get_y_rules():
    promos = [
        {
            "id": 1,
            "name": "خصم منتج",
            "apply_to": "product",
            "apply_to_id": 10,
            "min_quantity": 2,
            "promo_type": "percentage",
            "value": 10,
        },
        {
            "id": 2,
            "name": "خصم فئة",
            "apply_to": "category",
            "apply_to_id": 5,
            "min_quantity": 1,
            "promo_type": "fixed",
            "value": 7,
        },
        {
            "id": 3,
            "name": "اشتري وخذ",
            "apply_to": "all",
            "min_quantity": 1,
            "promo_type": "buy_x_get_y",
            "buy_quantity": 2,
            "value": 1,
        },
    ]
    repo = invoice_repo_with(fetch_one=[{"category_id": 5}, {"category_id": 6}])
    repo.get_active_promotions = lambda: promos

    applied, total = repo.calculate_promotions(
        [
            {"product_id": 10, "quantity": 2, "price": 50},
            {"product_id": 20, "quantity": 3, "price": 10},
        ]
    )

    assert total == 20.0
    assert applied == [
        {
            "promo_name": "خصم منتج",
            "promo_id": 1,
            "product_id": 10,
            "quantity": 2,
            "discount_amount": 10.0,
            "company_discount_amount": 10.0,
            "funding_source": "company",
            "supplier_id": None,
            "promo_type": "percentage",
        },
        {
            "promo_name": "اشتري وخذ",
            "promo_id": 3,
            "product_id": 20,
            "quantity": 3,
            "discount_amount": 10.0,
            "company_discount_amount": 10.0,
            "funding_source": "company",
            "supplier_id": None,
            "promo_type": "buy_x_get_y",
        },
    ]


def test_calculate_promotions_returns_empty_without_promos_or_items():
    repo = invoice_repo_with()
    repo.get_active_promotions = lambda: []

    assert repo.calculate_promotions([{"product_id": 1}]) == ([], 0.0)
    assert repo.calculate_promotions([]) == ([], 0.0)


def test_calculate_promotions_applies_second_item_discount():
    repo = invoice_repo_with(fetch_one={"category_id": 5})
    repo.get_active_promotions = lambda: [
        {
            "id": 9,
            "name": "خصم القطعة الثانية",
            "apply_to": "product",
            "apply_to_id": 10,
            "min_quantity": 2,
            "promo_type": "second_item_percentage",
            "value": 30,
        }
    ]

    applied, total = repo.calculate_promotions(
        [{"product_id": 10, "quantity": 5, "price": 100}]
    )

    assert total == 60.0
    assert applied[0]["discount_amount"] == 60.0
    assert applied[0]["promo_type"] == "second_item_percentage"


def test_record_supplier_promotion_claims_inserts_claim_and_ledger_entry():
    repo = invoice_repo_with(fetch_one={"exists": 1})

    repo.record_supplier_promotion_claims(
        sale_invoice_id=15,
        invoice_number="15",
        user_id=3,
        claims=[
            {
                "supplier_id": 7,
                "promotion_id": 5,
                "product_id": 10,
                "quantity": 2,
                "amount": 11.5,
                "description": "عرض مورد",
            }
        ],
    )

    execute_calls = [call for call in repo.calls if call[0] == "execute"]
    assert "INSERT INTO supplier_promotion_claims" in execute_calls[0][1]
    assert execute_calls[0][2] == (7, 5, 15, 10, 2.0, 11.5, "عرض مورد")
    assert "INSERT INTO financial_ledger" in execute_calls[1][1]
    assert execute_calls[1][2] == (7, 11.5, 15, "عرض مورد", 3)


def test_get_product_cross_branch_stock_returns_product_and_branch_stock():
    product = {"id": 10, "product_name": "منتج"}
    stocks = [{"store_id": 1, "quantity": 5}]
    repo = invoice_repo_with(fetch_one=product, fetch_all=stocks)

    result = repo.get_product_cross_branch_stock("P10")

    assert result == {"product": product, "stocks": stocks}
    assert "ORDER BY CASE" in repo.calls[0][1]
    assert repo.calls[0][2] == ("P10", "P10", "%P10%", "P10", "P10")
    assert "COALESCE(s.is_active, TRUE) = TRUE" in repo.calls[1][1]
    assert "COALESCE(s.store_type, 'Branch') != 'GM'" in repo.calls[1][1]
    assert repo.calls[1][2] == (10,)
