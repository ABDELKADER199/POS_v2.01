from application.use_cases.returns import (
    ProcessReturnUseCase,
    ReturnInvoiceQueryUseCase,
    ReturnsDrawerQueryUseCase,
    ReturnsHistoryUseCase,
)


class ReturnsServiceFacade:
    def __init__(self, repo):
        self.invoice_query_use_case = ReturnInvoiceQueryUseCase(repo)
        self.process_return_use_case = ProcessReturnUseCase(repo)
        self.history_use_case = ReturnsHistoryUseCase(repo)
        self.drawer_query_use_case = ReturnsDrawerQueryUseCase(repo)

    def search_invoice(self, invoice_number: str):
        return self.invoice_query_use_case.search_invoice(invoice_number)

    def get_invoice_items(self, invoice_id: int):
        return self.invoice_query_use_case.get_invoice_items(invoice_id)

    def process_return(
        self, invoice_id, items, reason, user_id, store_id, drawer_id=None
    ):
        return self.process_return_use_case.execute(
            invoice_id,
            items,
            reason,
            user_id,
            store_id,
            drawer_id,
        )

    def get_last_return_error(self):
        return self.process_return_use_case.last_error

    def get_returns_history(self, **kwargs):
        return self.history_use_case.execute(**kwargs)

    def get_drawer_status(self, user_id):
        return self.drawer_query_use_case.get_drawer_status(user_id)

    def get_store_open_drawer(self, store_id):
        return self.drawer_query_use_case.get_store_open_drawer(store_id)
