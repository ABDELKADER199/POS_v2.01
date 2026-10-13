from typing import List, Optional, Protocol

from models.user import User


class AuthRepositoryPort(Protocol):
    def authenticate(self, email: str, password: str) -> Optional[User]:
        ...

    def get_by_id(self, user_id: int) -> Optional[User]:
        ...

    def get_all(self, active_only: bool = True) -> List[User]:
        ...
