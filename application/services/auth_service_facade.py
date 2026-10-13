from typing import Optional

from application.use_cases.auth import CurrentUserInfoUseCase, LoginUseCase, LogoutUseCase
from models.user import User
from utils.device_identity import get_current_device_info
from utils.feature_flags import get_store_scope, is_role_allowed
from utils.permissions import ROLE_ADMIN, ROLE_DEVELOPER, ROLE_OWNER

import logging

logger = logging.getLogger(__name__)


class AuthServiceFacade:
    def __init__(self, repo, device_repo=None):
        self.login_use_case = LoginUseCase(repo)
        self.logout_use_case = LogoutUseCase()
        self.current_user_info_use_case = CurrentUserInfoUseCase()
        self.device_repo = device_repo
        self.current_user: Optional[User] = None

    def login(self, username: str, password: str) -> Optional[User]:
        user = self.login_use_case.execute(username, password)
        if not user:
            return None
        if not is_role_allowed(user.role_id):
            logger.warning(
                "Login blocked by edition role policy: user=%s role_id=%s",
                user.email,
                user.role_id,
            )
            return None
        self._apply_store_scope(user)
        if not self._is_device_authorized(user):
            logger.warning("Login blocked by device policy: user=%s", user.email)
            return None
        self.current_user = user
        return user

    def logout(self):
        self.logout_use_case.execute(self.current_user)
        self.current_user = None

    @property
    def is_authenticated(self) -> bool:
        return self.current_user is not None

    @property
    def user_info(self) -> dict:
        return self.current_user_info_use_case.execute(self.current_user)

    def _apply_store_scope(self, user: User) -> None:
        if user.role_id in (ROLE_DEVELOPER, ROLE_OWNER, ROLE_ADMIN):
            return
        scope = get_store_scope()
        if not scope:
            return
        user.store_id = int(scope["id"])
        if scope.get("name"):
            user.store_name = str(scope["name"])

    def _is_device_authorized(self, user: User) -> bool:
        if not self.device_repo:
            return True
        try:
            active_devices = self.device_repo.count_active_authorized_devices()
            if active_devices <= 0:
                return True
            device = get_current_device_info()
            record = self.device_repo.get_authorized_device_for_login(
                device.get("device_id", ""),
                device.get("mac_address", ""),
                user.id,
                user.store_id,
            )
            if not record:
                if user.role_id in (ROLE_DEVELOPER, ROLE_OWNER):
                    self.device_repo.upsert_authorized_device(
                        device.get("device_id", ""),
                        device.get("device_name", ""),
                        device.get("mac_address", ""),
                        user.store_id,
                        user.id,
                        user.id,
                        "Auto-registered privileged login device",
                    )
                    self.device_repo.commit()
                    logger.info("Privileged device auto-registered: user=%s", user.email)
                    return True
                return False
            self.device_repo.mark_authorized_device_used(record["id"])
            self.device_repo.commit()
            return True
        except Exception as exc:
            logger.error("Device authorization check failed: %s", exc, exc_info=True)
            return False
