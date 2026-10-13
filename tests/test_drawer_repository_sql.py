from repositories.drawer_repo import DrawerRepository


def drawer_repo_with(fetch_one=None, fetch_all=None, last_id=88):
    repo = DrawerRepository.__new__(DrawerRepository)
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


def test_get_store_open_drawer_fetches_latest_open_drawer_for_branch():
    drawer = {"id": 5, "store_id": 2, "cashier_id": 9}
    repo = drawer_repo_with(fetch_one=drawer)

    result = repo.get_store_open_drawer(2)

    assert result == drawer
    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "FROM drawer_logs dl" in query
    assert "JOIN users u ON dl.cashier_id = u.id" in query
    assert "LEFT JOIN stores s ON dl.store_id = s.id" in query
    assert "WHERE dl.store_id = %s" in query
    assert "AND dl.status = 'Open'" in query
    assert "COALESCE(s.store_type, 'Branch') = 'Branch'" in query
    assert "ORDER BY dl.opening_date DESC LIMIT 1" in query
    assert params == (2,)


def test_get_any_open_drawer_fetches_latest_open_drawer_across_branches():
    drawer = {"id": 6, "store_id": 3, "cashier_id": 10}
    repo = drawer_repo_with(fetch_one=drawer)

    result = repo.get_any_open_drawer()

    assert result == drawer
    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "WHERE dl.status = 'Open'" in query
    assert "COALESCE(s.store_type, 'Branch') = 'Branch'" in query
    assert "ORDER BY dl.opening_date DESC LIMIT 1" in query
    assert params is None


def test_get_operational_stores_returns_only_branch_stores():
    repo = drawer_repo_with(fetch_all=[{"id": 2, "store_name": "فرع", "store_type": "Branch"}])

    assert repo.get_operational_stores() == [{"id": 2, "store_name": "فرع", "store_type": "Branch"}]

    query = repo.calls[0][1]
    assert "FROM stores" in query
    assert "is_active = TRUE" in query
    assert "COALESCE(store_type, 'Branch') = 'Branch'" in query


def test_get_drawer_status_returns_only_open_drawer_for_user():
    repo = drawer_repo_with(fetch_one={"id": 7, "is_open": 1})

    assert repo.get_drawer_status(12) == {"id": 7, "is_open": 1}

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "WHERE dl.cashier_id = %s" in query
    assert "AND dl.status = 'Open'" in query
    assert "COALESCE(s.store_type, 'Branch') = 'Branch'" in query
    assert "(dl.status = 'Open') as is_open" in query
    assert params == (12,)


def test_insert_open_drawer_creates_open_log_and_returns_new_id():
    repo = drawer_repo_with(last_id=99)

    drawer_id = repo.insert_open_drawer(store_id=2, user_id=12, opening_balance=150.5)

    assert drawer_id == 99
    execute_call = repo.calls[0]
    assert "INSERT INTO drawer_logs" in execute_call[1]
    assert "VALUES (%s, %s, %s, 'Open')" in execute_call[1]
    assert execute_call[2] == (2, 12, 150.5)


def test_mark_drawer_closed_updates_open_drawer_only():
    repo = drawer_repo_with()

    repo.mark_drawer_closed(drawer_id=99, closing_balance=740.25)

    execute_call = repo.calls[0]
    assert "UPDATE drawer_logs" in execute_call[1]
    assert "SET status = 'Closed', closing_balance = %s, closing_date = NOW()" in execute_call[1]
    assert "WHERE id = %s AND status = 'Open'" in execute_call[1]
    assert execute_call[2] == (740.25, 99)


def test_replace_closing_details_replaces_cash_and_visa_totals():
    repo = drawer_repo_with()

    repo.replace_closing_details(99, {"Cash": 740.25, "Visa": 120.0})

    assert repo.calls[0] == (
        "execute",
        "DELETE FROM drawer_closing_details WHERE drawer_log_id = %s",
        (99,),
    )
    cash_call = repo.calls[1]
    visa_call = repo.calls[2]
    assert "INSERT INTO drawer_closing_details" in cash_call[1]
    assert cash_call[2] == (99, "Cash", 1, 740.25)
    assert visa_call[2] == (99, "Visa", 1, 120.0)


def test_get_drawer_summary_calculates_expected_cash_and_differences():
    repo = drawer_repo_with(
        fetch_one=[
            {
                "id": 99,
                "opening_balance": 100,
                "closing_balance": 690,
                "cashier_name": "Cashier",
                "store_name": "Main",
                "opening_date": "2026-05-01 09:00:00",
                "closing_date": "2026-05-01 17:00:00",
            },
            {
                "count": 4,
                "total_sales": 1000,
                "total_cash": 650,
                "total_card": 250,
            },
            {"total_returns": 80, "count": 2},
            {"cash_returns": 60},
        ],
        fetch_all=[
            {"denomination": "Cash", "quantity": 1, "total_amount": 690},
            {"denomination": "Visa", "quantity": 1, "total_amount": 240},
        ],
    )

    summary = repo.get_drawer_summary(99)

    assert summary["drawer_id"] == 99
    assert summary["opening_balance"] == 100.0
    assert summary["total_sales"] == 1000.0
    assert summary["total_cash_sales"] == 650.0
    assert summary["total_card_sales"] == 250.0
    assert summary["total_deferred"] == 100.0
    assert summary["total_returns"] == 80.0
    assert summary["total_cash_returns"] == 60.0
    assert summary["expected_cash"] == 690.0
    assert summary["actual_cash"] == 690.0
    assert summary["difference"] == 0.0
    assert summary["actual_visa"] == 240.0
    assert summary["visa_difference"] == -10.0


def test_get_drawer_summary_returns_empty_dict_when_drawer_missing():
    repo = drawer_repo_with(fetch_one=None)

    assert repo.get_drawer_summary(404) == {}
    assert len(repo.calls) == 1
    assert "WHERE dl.id = %s" in repo.calls[0][1]
    assert repo.calls[0][2] == (404,)


def test_closed_drawers_history_applies_optional_date_range():
    repo = drawer_repo_with(fetch_all=[])

    assert repo.get_closed_drawers_history(2, "2026-05-01", "2026-05-31") == []

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "WHERE dl.store_id = %s AND dl.status = 'Closed'" in query
    assert "AND DATE(dl.closing_date) BETWEEN %s AND %s" in query
    assert "ORDER BY dl.closing_date DESC" in query
    assert params == (2, "2026-05-01", "2026-05-31")


def test_closed_drawers_history_limits_latest_without_date_range():
    repo = drawer_repo_with(fetch_all=[])

    assert repo.get_closed_drawers_history(2) == []

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "WHERE dl.store_id = %s AND dl.status = 'Closed'" in query
    assert "ORDER BY dl.closing_date DESC LIMIT 50" in query
    assert params == (2,)


def test_get_last_closed_drawer_id_returns_latest_closed_drawer_id():
    repo = drawer_repo_with(fetch_one={"id": 44})

    assert repo.get_last_closed_drawer_id(store_id=2, user_id=12) == 44

    query = repo.calls[0][1]
    params = repo.calls[0][2]
    assert "WHERE store_id = %s AND cashier_id = %s AND status = 'Closed'" in query
    assert "ORDER BY closing_date DESC LIMIT 1" in query
    assert params == (2, 12)


def test_get_last_closed_drawer_id_returns_none_when_missing():
    repo = drawer_repo_with(fetch_one=None)

    assert repo.get_last_closed_drawer_id(store_id=2, user_id=12) is None
