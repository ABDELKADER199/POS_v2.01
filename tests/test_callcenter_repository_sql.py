from repositories.callcenter_repo import CallCenterRepository


def callcenter_repo_with(fetch_one=None, fetch_all=None, last_id=123):
    repo = CallCenterRepository.__new__(CallCenterRepository)
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


def test_get_all_stores_returns_active_stores_ordered_by_id():
    repo = callcenter_repo_with(fetch_all=[{"id": 1, "store_name": "Main"}])

    assert repo.get_all_stores() == [{"id": 1, "store_name": "Main"}]

    call = repo.calls[0]
    assert call[0] == "fetch_all"
    assert "FROM stores" in call[1]
    assert "COALESCE(is_active, TRUE) = TRUE" in call[1]
    assert "COALESCE(store_type, 'Branch') != 'GM'" in call[1]
    assert "ORDER BY id" in call[1]


def test_search_products_uses_name_code_and_barcode_like_filters():
    repo = callcenter_repo_with(fetch_all=[])

    assert repo.search_products("milk") == []

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "FROM products p" in query
    assert "LEFT JOIN categories c ON p.category_id = c.id" in query
    assert "WHERE p.is_active = TRUE" in query
    assert "p.product_name LIKE %s OR p.product_code LIKE %s OR p.barcode LIKE %s" in query
    assert "LIMIT 100" in query
    assert params == ("%milk%", "%milk%", "%milk%")


def test_get_customer_by_phone_fetches_customer_delivery_fields():
    customer = {"id": 7, "customer_name": "Customer"}
    repo = callcenter_repo_with(fetch_one=customer)

    assert repo.get_customer_by_phone("01000000000") == customer

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "name as customer_name" in query
    assert "address as customer_address" in query
    assert "FROM customers WHERE phone = %s LIMIT 1" in query
    assert params == ("01000000000",)


def test_update_customer_updates_only_supplied_fields():
    repo = callcenter_repo_with()

    repo.update_customer(customer_id=7, name="New Name", address="")

    assert len(repo.calls) == 1
    execute_call = repo.calls[0]
    assert execute_call[1] == "UPDATE customers SET name = %s WHERE id = %s"
    assert execute_call[2] == ("New Name", 7)

    repo.update_customer(customer_id=7, name="", address="New Address")

    execute_call = repo.calls[1]
    assert execute_call[1] == "UPDATE customers SET address = %s WHERE id = %s"
    assert execute_call[2] == ("New Address", 7)


def test_update_customer_skips_empty_updates():
    repo = callcenter_repo_with()

    repo.update_customer(customer_id=7, name="", address="")

    assert repo.calls == []


def test_create_customer_inserts_nullable_phone_and_address_and_returns_id():
    repo = callcenter_repo_with(last_id=55)

    customer_id = repo.create_customer("Customer", "", "")

    assert customer_id == 55
    execute_call = repo.calls[0]
    assert execute_call[1] == "INSERT INTO customers (name, phone, address) VALUES (%s, %s, %s)"
    assert execute_call[2] == ("Customer", None, None)


def test_create_order_header_inserts_pending_order_and_returns_id():
    repo = callcenter_repo_with(last_id=77)

    order_id = repo.create_order_header(
        order_number="CC-1",
        customer_name="Customer",
        phone="01000000000",
        address="Address",
        customer_city=None,
        customer_id=7,
        source_store_id=1,
        destination_store_id=2,
        user_id=5,
        total=150,
    )

    assert order_id == 77
    execute_call = repo.calls[0]
    assert "INSERT INTO orders" in execute_call[1]
    assert "call_center_user_id, total_amount, status" in execute_call[1]
    assert "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')" in execute_call[1]
    assert execute_call[2] == ("CC-1", "Customer", "01000000000", "Address", None, 7, 1, 2, 5, 150)


def test_insert_order_item_calculates_total_price_from_quantity_and_price():
    repo = callcenter_repo_with()

    repo.insert_order_item(order_id=77, product_id=10, quantity=3, price=12.5)

    execute_call = repo.calls[0]
    assert "INSERT INTO order_items" in execute_call[1]
    assert "(order_id, product_id, quantity, unit_price, total_price)" in execute_call[1]
    assert execute_call[2] == (77, 10, 3, 12.5, 37.5)


def test_get_orders_applies_status_store_and_search_filters():
    repo = callcenter_repo_with(fetch_all=[])

    result = repo.get_orders(statuses=["Pending", "Confirmed"], store_id=2, search="010")

    assert result == []
    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "FROM orders o" in query
    assert "LEFT JOIN stores dst ON o.destination_store_id = dst.id" in query
    assert "LEFT JOIN stores src ON o.source_store_id = src.id" in query
    assert "o.status IN (%s, %s)" in query
    assert "COALESCE(o.destination_store_id, o.source_store_id) = %s" in query
    assert "(o.order_number LIKE %s OR o.customer_name LIKE %s OR o.customer_phone LIKE %s)" in query
    assert "ORDER BY o.order_date DESC LIMIT 1000" in query
    assert params == ("Pending", "Confirmed", 2, "%010%", "%010%", "%010%")


def test_get_orders_without_filters_has_no_where_clause():
    repo = callcenter_repo_with(fetch_all=[])

    assert repo.get_orders() == []

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert " WHERE " not in query
    assert "ORDER BY o.order_date DESC LIMIT 1000" in query
    assert params == ()


def test_get_delivery_agents_filters_active_delivery_roles_by_store():
    repo = callcenter_repo_with(fetch_all=[])

    assert repo.get_delivery_agents(2) == []

    query = repo.calls[0][1]
    assert "JOIN roles r ON r.id = u.role_id" in query
    assert "u.store_id = %s" in query
    assert "COALESCE(u.is_active, TRUE) = TRUE" in query
    assert "r.role_name IN ('delivery', 'delivery_agent')" in query
    assert repo.calls[0][2] == (2,)


def test_assign_and_update_delivery_status_use_expected_parameters():
    repo = callcenter_repo_with()

    repo.assign_delivery_agent(10, 44)
    assert repo.calls[0][2] == (44, 10)
    assert "delivery_status = 'Assigned'" in repo.calls[0][1]

    repo.update_delivery_status(10, "OutForDelivery", "On route")
    assert repo.calls[1][2] == ("OutForDelivery", "On route", 10)
    assert "delivery_notes = COALESCE(%s, delivery_notes)" in repo.calls[1][1]


def test_get_order_details_joins_products_for_display_data():
    repo = callcenter_repo_with(fetch_all=[])

    assert repo.get_order_details(77) == []

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "FROM order_items oi" in query
    assert "JOIN products p ON oi.product_id = p.id" in query
    assert "WHERE oi.order_id = %s" in query
    assert params == (77,)


def test_get_order_by_id_includes_target_source_and_agent_names():
    order = {"id": 77, "order_number": "CC-1"}
    repo = callcenter_repo_with(fetch_one=order)

    assert repo.get_order_by_id(77) == order

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "dst.store_name as target_store" in query
    assert "src.store_name as source_store" in query
    assert "u.name as agent_name" in query
    assert "LEFT JOIN users u ON o.call_center_user_id = u.id" in query
    assert "WHERE o.id = %s" in query
    assert params == (77,)


def test_update_order_status_updates_status_by_id():
    repo = callcenter_repo_with()

    repo.update_order_status(77, "Delivered")

    assert repo.calls == [
        (
            "execute",
            "UPDATE orders SET status = %s WHERE id = %s",
            ("Delivered", 77),
        )
    ]
