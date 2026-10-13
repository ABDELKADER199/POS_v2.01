from repositories.transfers_repo import TransfersRepository


def transfers_repo_with(rows=None):
    repo = TransfersRepository.__new__(TransfersRepository)
    repo.rows = rows or []
    repo.calls = []

    def fetch_all(query, params=None):
        repo.calls.append(("fetch_all", query, params))
        return repo.rows

    repo._fetch_all = fetch_all
    return repo


def test_get_stores_excludes_general_manager_store():
    repo = transfers_repo_with(rows=[{"id": 1, "store_name": "Main", "store_type": "Branch"}])

    assert repo.get_stores() == [{"id": 1, "store_name": "Main", "store_type": "Branch"}]

    query = repo.calls[0][1]
    assert "FROM stores" in query
    assert "COALESCE(is_active, TRUE) = TRUE" in query
    assert "COALESCE(store_type, 'Branch') != 'GM'" in query
