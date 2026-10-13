from application.use_cases.admin import (
    AdminDevicesUseCase,
    AdminDrawersUseCase,
    AdminStoresUseCase,
    AdminSyncStatsUseCase,
    AdminUsersUseCase,
    InitializeAdminUseCase,
)


class AdminServiceFacade:
    def __init__(self, repo):
        self.initialize_use_case = InitializeAdminUseCase(repo)
        self.users_use_case = AdminUsersUseCase(repo)
        self.stores_use_case = AdminStoresUseCase(repo)
        self.drawers_use_case = AdminDrawersUseCase(repo)
        self.devices_use_case = AdminDevicesUseCase(repo)
        self.sync_stats_use_case = AdminSyncStatsUseCase(repo)
        self.initialize_use_case.execute()

    def get_all_users(self):
        return self.users_use_case.get_all()

    def get_user_by_email(self, email):
        return self.users_use_case.get_by_email(email)

    def get_all_roles(self):
        return self.users_use_case.get_roles()

    def get_all_stores(self, include_inactive=False):
        return self.stores_use_case.get_all(include_inactive)

    def add_user(self, name, email, password, role_id, store_id, phone=""):
        return self.users_use_case.add(name, email, password, role_id, store_id, phone)

    def update_user(self, user_id, name, email, role_id, store_id, phone="", password=None):
        return self.users_use_case.update(user_id, name, email, role_id, store_id, phone, password)

    def delete_user(self, user_id):
        return self.users_use_case.delete(user_id)

    def get_drawers_report(self):
        return self.drawers_use_case.get_report()

    def get_drawer_summary(self, drawer_id):
        return self.drawers_use_case.get_summary(drawer_id)

    def add_store(
        self,
        name,
        store_type,
        city="",
        address="",
        phone="",
        manager="",
        ip_start=None,
        ip_end=None,
        require_ip_check=True,
        is_active=True,
    ):
        return self.stores_use_case.add(
            name,
            store_type,
            city,
            address,
            phone,
            manager,
            ip_start,
            ip_end,
            require_ip_check,
            is_active,
        )

    def update_store(
        self,
        store_id,
        name,
        store_type,
        city="",
        address="",
        phone="",
        manager="",
        ip_start=None,
        ip_end=None,
        require_ip_check=True,
        is_active=True,
    ):
        return self.stores_use_case.update(
            store_id,
            name,
            store_type,
            city,
            address,
            phone,
            manager,
            ip_start,
            ip_end,
            require_ip_check,
            is_active,
        )

    def delete_store(self, store_id):
        return self.stores_use_case.delete(store_id)

    def get_authorized_devices(self):
        return self.devices_use_case.get_all()

    def add_authorized_device(self, device_id, device_name, mac, store_id, user_id, reg_by, notes=""):
        return self.devices_use_case.add(device_id, device_name, mac, store_id, user_id, reg_by, notes)

    def update_device_status(self, device_id, is_active):
        return self.devices_use_case.update_status(device_id, is_active)

    def delete_device(self, device_id):
        return self.devices_use_case.delete(device_id)

    def get_sync_stats(self):
        return self.sync_stats_use_case.execute()
