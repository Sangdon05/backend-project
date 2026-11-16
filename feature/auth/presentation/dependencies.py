from typing import Annotated

from auth.application.service import AuthService
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from feature.user.domain.repository import UserRepository
from feature.user.domain.user import User
from feature.user.presentation.dependencies import provide_user_repository

from shared.core.exceptions import ForbiddenException, UnauthorizedException


def provide_auth_service() -> AuthService:
    raise NotImplementedError("AuthService 의존성이 주입되지 않았습니다.")
