from feature.board.application.service import BoardService, CommentService, PostService
from feature.board.domain.enums import Role
from feature.board.domain.post import Author
from feature.board.domain.repositories.board_repository import BoardRepository
from feature.board.domain.repositories.comment_repository import CommentRepository
from feature.board.domain.repositories.post_repository import PostRepository


# Repository 의존성
def provide_board_repository() -> BoardRepository:
    raise NotImplementedError("BoardRepository 의존성이 주입되지 않았습니다.")


def provide_post_repository() -> PostRepository:
    raise NotImplementedError("PostRepository 의존성이 주입되지 않았습니다.")


def provide_comment_repository() -> CommentRepository:
    raise NotImplementedError("CommentRepository 의존성이 주입되지 않았습니다.")


# Service 의존성
def provide_board_service() -> BoardService:
    """FastAPI Depends 플레이스홀더 (wiring/board.py에서 바인딩)"""
    raise NotImplementedError("BoardService 의존성이 주입되지 않았습니다.")


def provide_post_service() -> PostService:
    raise NotImplementedError("PostService 의존성이 주입되지 않았습니다.")


def provide_comment_service() -> CommentService:
    raise NotImplementedError("CommentService 의존성이 주입되지 않았습니다.")


async def get_current_role() -> Role:
    """
    현재 요청자의 권한 Role 반환
    - 비회원 / 미인증: Role.ALL
    - 로그인 일반회원: Role.USER
    - 관리자: Role.ADMIN
    """
    raise NotImplementedError("get_current_role 의존성이 주입되지 않았습니다.")


async def require_admin_role() -> Role:
    """게시판 설정 변경 등을 위한 관리자 Role 검증 플레이스홀더"""
    raise NotImplementedError("require_admin_role 의존성이 주입되지 않았습니다.")


async def get_current_author() -> Author | None:
    """
    현재 요청자의 회원 작성자 객체 반환 (플레이스홀더)
    - 로그인 회원: Author.member(user_id, username)
    - 비회원: None
    """
    raise NotImplementedError("get_current_author 의존성이 주입되지 않았습니다.")
