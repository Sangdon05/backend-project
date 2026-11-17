import os
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from feature.auth.application.service import AuthService
from feature.auth.infrastructure.credentials_verifier import UserCredentialVerifierImpl
from feature.auth.infrastructure.repositories import SqlAlchemyTokenBlacklistRepository
from feature.auth.infrastructure.security import JwtTokenProvider
from feature.auth.presentation.dependencies import (
    authenticate_user,
    authorize_admin,
    provide_auth_service,
)
from feature.user.domain.repository import UserRepository
from feature.user.presentation.dependencies import (
    get_current_user,
    provide_user_repository,
    require_admin,
)
from shared.core.database import get_db
from wiring.user import password_hasher


def wire_auth(app: FastAPI) -> None:
    # 시크릿 미설정 시 기동 단계에서 실패시킨다
    token_provider = JwtTokenProvider(
        secret_key=os.getenv("JWT_SECRET_KEY", ""),
        access_token_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "60")),
    )

    def build_auth_service(
        session: Annotated[AsyncSession, Depends(get_db)],
        user_repo: Annotated[UserRepository, Depends(provide_user_repository)],
    ) -> AuthService:
        return AuthService(
            credential_verifier=UserCredentialVerifierImpl(user_repo, password_hasher),
            token_blacklist_repo=SqlAlchemyTokenBlacklistRepository(session),
            token_provider=token_provider,
        )

    app.dependency_overrides[provide_auth_service] = build_auth_service
    app.dependency_overrides[get_current_user] = authenticate_user
    app.dependency_overrides[require_admin] = authorize_admin
