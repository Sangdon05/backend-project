from typing import Annotated

from fastapi import Depends

from feature.auth.application.service import AuthService
from feature.user.domain.repository import UserRepository
from feature.user.domain.user import User
from feature.user.presentation.dependencies import (
    get_current_user,
    provide_user_repository,
)
from shared.core.exceptions import ForbiddenException, UnauthorizedException
from shared.core.security import BearerCredentials


def provide_auth_service() -> AuthService:
    raise NotImplementedError("AuthService 의존성이 주입되지 않았습니다.")


async def get_bearer_token(
    credentials: BearerCredentials,
) -> str:
    """Authorization: Bearer 헤더에서 토큰 문자열 추출"""
    if credentials is None:
        raise UnauthorizedException("인증 토큰이 필요합니다.")
    return credentials.credentials


async def _resolve_user(
    token: str, auth_service: AuthService, user_repo: UserRepository
) -> User:
    """토큰 검증(서명/만료/블랙리스트) 후 활성 사용자 반환"""
    payload = await auth_service.authenticate_token(token)
    user = await user_repo.find_by_id(payload.user_id)
    if not user or user.resign:
        raise UnauthorizedException("유효하지 않은 사용자입니다.")
    return user


async def authenticate_user(
    token: Annotated[str, Depends(get_bearer_token)],
    auth_service: Annotated[AuthService, Depends(provide_auth_service)],
    user_repo: Annotated[UserRepository, Depends(provide_user_repository)],
) -> User:
    """로그인 필수 — get_current_user 구현체"""
    return await _resolve_user(token, auth_service, user_repo)


async def authenticate_optional_user(
    credentials: BearerCredentials,
    auth_service: Annotated[AuthService, Depends(provide_auth_service)],
    user_repo: Annotated[UserRepository, Depends(provide_user_repository)],
) -> User | None:
    """로그인 선택 — 토큰이 없으면 비회원(None), 있으면 검증 (잘못된 토큰은 401)"""
    if credentials is None:
        return None
    return await _resolve_user(credentials.credentials, auth_service, user_repo)


async def authorize_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """관리자 권한 검증 — require_admin 구현체"""
    if user.role != "ADMIN":
        raise ForbiddenException("관리자 권한이 필요합니다.")
    return user
