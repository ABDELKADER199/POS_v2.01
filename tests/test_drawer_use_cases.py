from application.use_cases.manage_drawer import (
    CLOSE_OWN_DRAWER_ACTION,
    OPEN_DRAWER_ACTION,
    CloseDrawerUseCase,
    DrawerQueryUseCase,
    OpenDrawerUseCase,
)


class FakeDrawerRepository:
    def __init__(self):
        self.calls = []
        self.existing_drawer = None
        self.inserted_drawer_id = 55
        self.raise_on_insert = None
        self.raise_on_close = None
        self.committed = False
        self.rolled_back = False

    def get_store_open_drawer(self, store_id):
        self.calls.append(("get_store_open_drawer", store_id))
        return self.existing_drawer

    def get_any_open_drawer(self):
        self.calls.append(("get_any_open_drawer",))
        return self.existing_drawer

    def get_drawer_status(self, user_id):
        self.calls.append(("get_drawer_status", user_id))
        return self.existing_drawer

    def get_drawer_summary(self, drawer_id):
        self.calls.append(("get_drawer_summary", drawer_id))
        return {"drawer_id": drawer_id}

    def get_open_drawer_summary(self, drawer_id):
        self.calls.append(("get_open_drawer_summary", drawer_id))
        return {"drawer_id": drawer_id, "status": "Open"}

    def get_closed_drawers_history(self, store_id, date_from=None, date_to=None):
        self.calls.append(("get_closed_drawers_history", store_id, date_from, date_to))
        return [{"store_id": store_id}]

    def get_last_closed_drawer_id(self, store_id, user_id):
        self.calls.append(("get_last_closed_drawer_id", store_id, user_id))
        return 44

    def insert_open_drawer(self, store_id, user_id, opening_balance):
        self.calls.append(("insert_open_drawer", store_id, user_id, opening_balance))
        if self.raise_on_insert:
            raise self.raise_on_insert
        return self.inserted_drawer_id

    def mark_drawer_closed(self, drawer_id, closing_balance):
        self.calls.append(("mark_drawer_closed", drawer_id, closing_balance))
        if self.raise_on_close:
            raise self.raise_on_close

    def replace_closing_details(self, drawer_id, denomination_details):
        self.calls.append(("replace_closing_details", drawer_id, denomination_details))

    def commit(self):
        self.calls.append(("commit",))
        self.committed = True

    def rollback(self):
        self.calls.append(("rollback",))
        self.rolled_back = True


class FakeAudit:
    def __init__(self):
        self.entries = []

    def log(
        self,
        user_id,
        action,
        entity_type="",
        entity_id=None,
        store_id=None,
        success=True,
        details=None,
    ):
        self.entries.append(
            {
                "user_id": user_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "store_id": store_id,
                "success": success,
                "details": details or {},
            }
        )


def call_names(repo):
    return [call[0] for call in repo.calls]


def test_open_drawer_commits_and_writes_audit():
    repo = FakeDrawerRepository()
    audit = FakeAudit()
    use_case = OpenDrawerUseCase(repo, audit)

    result = use_case.execute(store_id=1, user_id=2, opening_balance=100)

    assert result is True
    assert repo.committed is True
    assert repo.rolled_back is False
    assert ("insert_open_drawer", 1, 2, 100) in repo.calls
    assert audit.entries == [
        {
            "user_id": 2,
            "action": OPEN_DRAWER_ACTION,
            "entity_type": "drawer",
            "entity_id": 55,
            "store_id": 1,
            "success": True,
            "details": {"opening_balance": 100},
        }
    ]


def test_open_drawer_refuses_when_branch_already_has_open_drawer():
    repo = FakeDrawerRepository()
    repo.existing_drawer = {"id": 9, "cashier_id": 7}
    audit = FakeAudit()
    use_case = OpenDrawerUseCase(repo, audit)

    result = use_case.execute(store_id=1, user_id=2, opening_balance=100)

    assert result is False
    assert "insert_open_drawer" not in call_names(repo)
    assert repo.committed is False
    assert repo.rolled_back is False
    assert audit.entries == []


def test_open_drawer_refuses_missing_store_id_before_insert():
    repo = FakeDrawerRepository()
    audit = FakeAudit()
    use_case = OpenDrawerUseCase(repo, audit)

    result = use_case.execute(store_id=None, user_id=2, opening_balance=100)

    assert result is False
    assert "get_store_open_drawer" not in call_names(repo)
    assert "insert_open_drawer" not in call_names(repo)
    assert repo.committed is False
    assert repo.rolled_back is False
    assert audit.entries == [
        {
            "user_id": 2,
            "action": OPEN_DRAWER_ACTION,
            "entity_type": "drawer",
            "entity_id": None,
            "store_id": None,
            "success": False,
            "details": {"opening_balance": 100, "error": "missing_store_id"},
        }
    ]


def test_open_drawer_rolls_back_and_audits_failure():
    repo = FakeDrawerRepository()
    repo.raise_on_insert = RuntimeError("db error")
    audit = FakeAudit()
    use_case = OpenDrawerUseCase(repo, audit)

    result = use_case.execute(store_id=1, user_id=2, opening_balance=100)

    assert result is False
    assert repo.committed is False
    assert repo.rolled_back is True
    assert audit.entries[0]["action"] == OPEN_DRAWER_ACTION
    assert audit.entries[0]["success"] is False
    assert audit.entries[0]["details"]["error"] == "db error"


def test_close_drawer_commits_closing_details_and_writes_audit():
    repo = FakeDrawerRepository()
    audit = FakeAudit()
    use_case = CloseDrawerUseCase(repo, audit)
    details = {"200": {"quantity": 2, "total": 400}}

    result = use_case.execute(
        drawer_id=55,
        closing_balance=500,
        denomination_details=details,
        user_id=2,
        store_id=1,
    )

    assert result is True
    assert ("mark_drawer_closed", 55, 500) in repo.calls
    assert ("replace_closing_details", 55, details) in repo.calls
    assert repo.committed is True
    assert repo.rolled_back is False
    assert audit.entries[0]["action"] == CLOSE_OWN_DRAWER_ACTION
    assert audit.entries[0]["entity_id"] == 55
    assert audit.entries[0]["success"] is True


def test_close_drawer_rolls_back_and_audits_failure():
    repo = FakeDrawerRepository()
    repo.raise_on_close = RuntimeError("close failed")
    audit = FakeAudit()
    use_case = CloseDrawerUseCase(repo, audit)

    result = use_case.execute(drawer_id=55, closing_balance=500, user_id=2, store_id=1)

    assert result is False
    assert repo.committed is False
    assert repo.rolled_back is True
    assert audit.entries[0]["action"] == CLOSE_OWN_DRAWER_ACTION
    assert audit.entries[0]["success"] is False
    assert audit.entries[0]["details"]["error"] == "close failed"


def test_drawer_query_use_case_delegates_to_repository():
    repo = FakeDrawerRepository()
    query = DrawerQueryUseCase(repo)

    assert query.get_store_open_drawer(1) is None
    assert query.get_any_open_drawer() is None
    assert query.get_drawer_status(2) is None
    assert query.get_drawer_summary(55) == {"drawer_id": 55}
    assert query.get_open_drawer_summary(55) == {"drawer_id": 55, "status": "Open"}
    assert query.get_closed_drawers_history(1, "2026-01-01", "2026-12-31") == [{"store_id": 1}]
    assert query.get_last_closed_drawer_id(1, 2) == 44


def test_drawer_query_returns_none_for_missing_store_id():
    repo = FakeDrawerRepository()
    query = DrawerQueryUseCase(repo)

    assert query.get_store_open_drawer(None) is None
    assert repo.calls == []
