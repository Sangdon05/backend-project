from feature.user.application.service import UserService
from feature.user.domain.repository import UserRepository
from feature.user.domain.user import User
from shared.core.security import BearerCredentials


def provide_user_service() -> UserService:
    raise NotImplementedError("UserService 의존성이 주입되지 않았습니다.")


def provide_user_repository() -> UserRepository:
    raise NotImplementedError("UserRepository 의존성이 주입되지 않았습니다.")


async def get_current_user(_: BearerCredentials) -> User:
    raise NotImplementedError("get_current_user 의존성이 주입되지 않았습니다.")


async def require_admin(_: BearerCredentials) -> User:
    raise NotImplementedError("require_admin 의존성이 주입되지 않았습니다.")
