import logging
from typing import Optional

from application.ports.auth_port import AuthRepositoryPort
from models.user import User

logger = logging.getLogger(__name__)


class LoginUseCase:
    def __init__(self, repo: AuthRepositoryPort):
        self.repo = repo

    def execute(self, username: str, password: str) -> Optional[User]:
        user = self.repo.authenticate(username, password)
        if user:
            logger.info("User logged in: %s (%s)", user.email, user.role)
        else:
            logger.warning("Failed login attempt: %s", username)
        return user


class LogoutUseCase:
    def execute(self, user: Optional[User]):
        if user:
            logger.info("User logged out: %s", user.email or user.name or user.id)


class CurrentUserInfoUseCase:
    def execute(self, user: Optional[User]) -> dict:
        if user:
            return user.to_dict()
        return {}
