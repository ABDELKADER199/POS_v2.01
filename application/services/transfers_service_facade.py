from application.use_cases.transfers import (
    CancelTransferUseCase,
    CreateTransferUseCase,
    ListTransfersUseCase,
    ReceiveTransferUseCase,
    TransferProductSearchUseCase,
    TransferStoresUseCase,
)


class TransfersServiceFacade:
    def __init__(self, repo):
        self.stores_use_case = TransferStoresUseCase(repo)
        self.product_search_use_case = TransferProductSearchUseCase(repo)
        self.list_transfers_use_case = ListTransfersUseCase(repo)
        self.create_transfer_use_case = CreateTransferUseCase(repo)
        self.receive_transfer_use_case = ReceiveTransferUseCase(repo)
        self.cancel_transfer_use_case = CancelTransferUseCase(repo)

    def get_stores(self):
        return self.stores_use_case.execute()

    def search_products(self, term, store_id=None):
        return self.product_search_use_case.execute(term, store_id)

    def get_transfers(self, user_info, status=None):
        return self.list_transfers_use_case.execute(user_info, status)

    def create_transfer(self, product_id, from_store_id, to_store_id, quantity, user_id, notes=""):
        return self.create_transfer_use_case.execute(
            product_id,
            from_store_id,
            to_store_id,
            quantity,
            user_id,
            notes,
        )

    def receive_transfer(self, transfer_id, user_info):
        return self.receive_transfer_use_case.execute(transfer_id, user_info)

    def cancel_transfer(self, transfer_id):
        return self.cancel_transfer_use_case.execute(transfer_id)
