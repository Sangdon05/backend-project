from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from feature.user.application.service import UserService
from feature.user.domain.repository import UserRepository
from feature.user.infrastructure.repositories import SqlAlchemyUserRepository
from feature.user.infrastructure.security import BcryptPasswordHasher
from feature.user.presentation.dependencies import (
    provide_user_repository,
    provide_user_service,
)
from shared.core.database import get_db

# 상태가 없는 구현체는 프로세스 단위 싱글턴으로 공유
password_hasher = BcryptPasswordHasher()


def build_user_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def build_user_service(
    repository: Annotated[UserRepository, Depends(provide_user_repository)],
) -> UserService:
    return UserService(repository=repository, hasher=password_hasher)


def wire_user(app: FastAPI) -> None:
    app.dependency_overrides[provide_user_repository] = build_user_repository
    app.dependency_overrides[provide_user_service] = build_user_service
