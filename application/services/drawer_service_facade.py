from application.use_cases.manage_drawer import (
    CloseDrawerUseCase,
    DrawerQueryUseCase,
    OpenDrawerUseCase,
)


class DrawerServiceFacade:
    def __init__(self, repo, audit):
        self.query_use_case = DrawerQueryUseCase(repo)
        self.open_use_case = OpenDrawerUseCase(repo, audit)
        self.close_use_case = CloseDrawerUseCase(repo, audit)

    def get_store_open_drawer(self, store_id):
        return self.query_use_case.get_store_open_drawer(store_id)

    def get_any_open_drawer(self):
        return self.query_use_case.get_any_open_drawer()

    def get_drawer_status(self, user_id):
        return self.query_use_case.get_drawer_status(user_id)

    def open_drawer(self, store_id, user_id, opening_balance):
        return self.open_use_case.execute(store_id, user_id, opening_balance)

    def close_drawer(
        self,
        drawer_id,
        closing_balance,
        denomination_details=None,
        user_id=None,
        store_id=None,
    ):
        return self.close_use_case.execute(
            drawer_id,
            closing_balance,
            denomination_details,
            user_id,
            store_id,
        )

    def get_drawer_summary(self, drawer_id):
        return self.query_use_case.get_drawer_summary(drawer_id)

    def get_open_drawer_summary(self, drawer_id):
        return self.query_use_case.get_open_drawer_summary(drawer_id)

    def get_closed_drawers_history(self, store_id, date_from=None, date_to=None):
        return self.query_use_case.get_closed_drawers_history(store_id, date_from, date_to)

    def get_last_closed_drawer_id(self, store_id, user_id):
        return self.query_use_case.get_last_closed_drawer_id(store_id, user_id)
