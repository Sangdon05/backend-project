from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from feature.auth.presentation.dependencies import authenticate_optional_user
from feature.board.application.service import BoardService, CommentService, PostService
from feature.board.domain.enums import Role
from feature.board.domain.post import Author
from feature.board.domain.repositories.board_repository import BoardRepository
from feature.board.domain.repositories.comment_repository import CommentRepository
from feature.board.domain.repositories.post_repository import PostRepository
from feature.board.infrastructure.security import BcryptPasswordHasher
from feature.board.infrastructure.sqlalchemy.board_repository import (
    SqlAlchemyBoardRepository,
)
from feature.board.infrastructure.sqlalchemy.comment_repository import (
    SqlAlchemyCommentRepository,
)
from feature.board.infrastructure.sqlalchemy.post_repository import (
    SqlAlchemyPostRepository,
)
from feature.board.presentation.dependencies import (
    get_current_author,
    get_current_role,
    provide_board_repository,
    provide_board_service,
    provide_comment_repository,
    provide_comment_service,
    provide_post_repository,
    provide_post_service,
    require_admin_role,
)
from feature.user.domain.user import User
from shared.core.database import get_db
from shared.core.exceptions import ForbiddenException

# 상태가 없는 구현체는 프로세스 단위 싱글턴으로 공유
password_hasher = BcryptPasswordHasher()

OptionalUser = Annotated[User | None, Depends(authenticate_optional_user)]


# Repository
def build_board_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BoardRepository:
    return SqlAlchemyBoardRepository(session)


def build_post_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PostRepository:
    return SqlAlchemyPostRepository(session)


def build_comment_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CommentRepository:
    return SqlAlchemyCommentRepository(session)


# Service
def build_board_service(
    board_repo: Annotated[BoardRepository, Depends(provide_board_repository)],
) -> BoardService:
    return BoardService(board_repo)


def build_post_service(
    post_repo: Annotated[PostRepository, Depends(provide_post_repository)],
    board_repo: Annotated[BoardRepository, Depends(provide_board_repository)],
) -> PostService:
    return PostService(post_repo, board_repo, password_hasher)


def build_comment_service(
    comment_repo: Annotated[CommentRepository, Depends(provide_comment_repository)],
    post_repo: Annotated[PostRepository, Depends(provide_post_repository)],
    board_repo: Annotated[BoardRepository, Depends(provide_board_repository)],
) -> CommentService:
    return CommentService(comment_repo, post_repo, board_repo, password_hasher)


# 요청자 식별 (user 피처의 User -> board 피처의 Role / Author 변환)
async def resolve_current_role(user: OptionalUser) -> Role:
    return Role(user.role) if user else Role.ALL


async def resolve_current_author(user: OptionalUser) -> Author | None:
    if not user or user.id is None:
        return None
    return Author.member(user.id, user.name)


async def resolve_admin_role(
    role: Annotated[Role, Depends(get_current_role)],
) -> Role:
    if role != Role.ADMIN:
        raise ForbiddenException("관리자 권한이 필요합니다.")
    return role


def wire_board(app: FastAPI) -> None:
    app.dependency_overrides[provide_board_repository] = build_board_repository
    app.dependency_overrides[provide_post_repository] = build_post_repository
    app.dependency_overrides[provide_comment_repository] = build_comment_repository
    app.dependency_overrides[provide_board_service] = build_board_service
    app.dependency_overrides[provide_post_service] = build_post_service
    app.dependency_overrides[provide_comment_service] = build_comment_service
    app.dependency_overrides[get_current_role] = resolve_current_role
    app.dependency_overrides[get_current_author] = resolve_current_author
    app.dependency_overrides[require_admin_role] = resolve_admin_role
