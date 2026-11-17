import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from feature.board.application.service import BoardService, CommentService, PostService
from feature.board.domain.board import Authority
from feature.board.domain.enums import Role
from feature.board.domain.post import Author
from feature.board.presentation.dependencies import (
    get_current_author,
    get_current_role,
    provide_board_service,
    provide_comment_service,
    provide_post_service,
    require_admin_role,
)
from feature.board.presentation.schemas import (
    AuthoritySchema,
    BoardResponse,
    CommentResponse,
    CreateBoardRequest,
    CreateCommentRequest,
    CreatePostRequest,
    DeleteCommentRequest,
    DeletePostRequest,
    PostDetailResponse,
    PostListItemResponse,
    PostPaginationResponse,
    PostSearchQuery,
    UpdateBoardRequest,
    UpdateCommentRequest,
    UpdatePostRequest,
)
from shared.core.exceptions import ValidationException
from shared.core.schemas import APIResponse

router = APIRouter(prefix="/v1")

BoardServiceDep = Annotated[BoardService, Depends(provide_board_service)]
PostServiceDep = Annotated[PostService, Depends(provide_post_service)]
CommentServiceDep = Annotated[CommentService, Depends(provide_comment_service)]
RoleDep = Annotated[Role, Depends(get_current_role)]
MemberDep = Annotated[Author | None, Depends(get_current_author)]
AdminDep = Annotated[Role, Depends(require_admin_role)]


def _to_authority(schema: AuthoritySchema | None) -> Authority | None:
    return Authority(**schema.model_dump()) if schema else None


def _resolve_author(member: Author | None, guest_name: str | None) -> Author:
    """로그인 회원이면 회원 작성자, 아니면 비회원 닉네임으로 작성자 생성"""
    if member:
        return member
    if not guest_name:
        raise ValidationException(
            message="비회원 작성 시 닉네임은 필수입니다.",
            field_errors={"guest_name": ["비회원 닉네임을 입력하세요."]},
        )
    return Author.guest(guest_name)


def _requester_id(member: Author | None):
    return member.author_id if member else None


# 게시판 설정
@router.post(
    "/boards",
    response_model=APIResponse[BoardResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["Boards"],
    summary="게시판 생성 (관리자)",
)
async def create_board(
    request: CreateBoardRequest, _: AdminDep, board_service: BoardServiceDep
):
    board = await board_service.create_board(
        board_id=request.board_id,
        board_name=request.board_name,
        authority=_to_authority(request.authority),
        page_size=request.page_size,
    )
    return APIResponse.ok(data=BoardResponse.from_domain(board))


@router.get(
    "/boards",
    response_model=APIResponse[list[BoardResponse]],
    tags=["Boards"],
    summary="게시판 목록",
)
async def list_boards(board_service: BoardServiceDep):
    boards = await board_service.get_all_boards()
    return APIResponse.ok(data=[BoardResponse.from_domain(b) for b in boards])


@router.get(
    "/boards/{board_id}",
    response_model=APIResponse[BoardResponse],
    tags=["Boards"],
    summary="게시판 설정 조회",
)
async def get_board(board_id: str, board_service: BoardServiceDep):
    board = await board_service.get_board(board_id)
    return APIResponse.ok(data=BoardResponse.from_domain(board))


@router.put(
    "/boards/{board_id}",
    response_model=APIResponse[BoardResponse],
    tags=["Boards"],
    summary="게시판 설정 수정 (관리자)",
)
async def update_board(
    board_id: str,
    request: UpdateBoardRequest,
    _: AdminDep,
    board_service: BoardServiceDep,
):
    board = await board_service.update_board_config(
        board_id=board_id,
        board_name=request.board_name,
        page_size=request.page_size,
        authority=_to_authority(request.authority),
    )
    return APIResponse.ok(data=BoardResponse.from_domain(board))


@router.delete(
    "/boards/{board_id}",
    response_model=APIResponse[None],
    tags=["Boards"],
    summary="게시판 삭제 (관리자, 소프트 삭제)",
)
async def delete_board(board_id: str, _: AdminDep, board_service: BoardServiceDep):
    await board_service.delete_board(board_id)
    return APIResponse.ok(message="게시판이 삭제되었습니다.")


# 게시글
@router.post(
    "/boards/{board_id}/posts",
    response_model=APIResponse[PostDetailResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["Posts"],
    summary="게시글 작성 (회원/비회원)",
)
async def write_post(
    board_id: str,
    request: CreatePostRequest,
    role: RoleDep,
    member: MemberDep,
    post_service: PostServiceDep,
):
    post = await post_service.write_post(
        board_id=board_id,
        title=request.title,
        content=request.content,
        author=_resolve_author(member, request.guest_name),
        raw_guest_password=request.guest_password,
        user_role=role,
    )
    return APIResponse.ok(data=PostDetailResponse.from_domain(post))


@router.get(
    "/boards/{board_id}/posts",
    response_model=APIResponse[PostPaginationResponse],
    tags=["Posts"],
    summary="게시글 목록 (페이징/검색)",
)
async def list_posts(
    board_id: str,
    query: Annotated[PostSearchQuery, Query()],
    role: RoleDep,
    post_service: PostServiceDep,
):
    posts, total_count, page_size = await post_service.list_posts(
        board_id=board_id,
        user_role=role,
        page=query.page,
        page_size=query.page_size,
        search_type=query.search_type,
        keyword=query.keyword,
    )
    return APIResponse.ok(
        data=PostPaginationResponse(
            items=[PostListItemResponse.from_domain(p) for p in posts],
            total_count=total_count,
            page=query.page,
            page_size=page_size,
            total_pages=math.ceil(total_count / page_size),
            search_type=query.search_type,
            keyword=query.keyword,
        )
    )


@router.get(
    "/posts/{post_id}",
    response_model=APIResponse[PostDetailResponse],
    tags=["Posts"],
    summary="게시글 상세",
)
async def get_post(post_id: int, role: RoleDep, post_service: PostServiceDep):
    post = await post_service.get_post_detail(post_id, user_role=role)
    return APIResponse.ok(data=PostDetailResponse.from_domain(post))


@router.put(
    "/posts/{post_id}",
    response_model=APIResponse[PostDetailResponse],
    tags=["Posts"],
    summary="게시글 수정 (작성자 본인/비회원 비밀번호/관리자)",
)
async def update_post(
    post_id: int,
    request: UpdatePostRequest,
    role: RoleDep,
    member: MemberDep,
    post_service: PostServiceDep,
):
    post = await post_service.update_post(
        post_id=post_id,
        title=request.title,
        content=request.content,
        requester_id=_requester_id(member),
        guest_password=request.guest_password,
        user_role=role,
    )
    return APIResponse.ok(data=PostDetailResponse.from_domain(post))


@router.delete(
    "/posts/{post_id}",
    response_model=APIResponse[None],
    tags=["Posts"],
    summary="게시글 삭제 (작성자 본인/비회원 비밀번호/관리자)",
)
async def delete_post(
    post_id: int,
    role: RoleDep,
    member: MemberDep,
    post_service: PostServiceDep,
    request: DeletePostRequest | None = None,
):
    await post_service.delete_post(
        post_id=post_id,
        requester_id=_requester_id(member),
        guest_password=request.guest_password if request else None,
        user_role=role,
    )
    return APIResponse.ok(message="게시글이 삭제되었습니다.")


# 댓글
@router.post(
    "/posts/{post_id}/comments",
    response_model=APIResponse[CommentResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["Comments"],
    summary="댓글 작성 (회원/비회원)",
)
async def write_comment(
    post_id: int,
    request: CreateCommentRequest,
    role: RoleDep,
    member: MemberDep,
    comment_service: CommentServiceDep,
):
    comment = await comment_service.write_comment(
        post_id=post_id,
        content=request.content,
        author=_resolve_author(member, request.guest_name),
        raw_guest_password=request.guest_password,
        user_role=role,
    )
    return APIResponse.ok(data=CommentResponse.from_domain(comment))


@router.get(
    "/posts/{post_id}/comments",
    response_model=APIResponse[list[CommentResponse]],
    tags=["Comments"],
    summary="댓글 목록 (등록순)",
)
async def list_comments(
    post_id: int, role: RoleDep, comment_service: CommentServiceDep
):
    comments = await comment_service.list_comments(post_id, user_role=role)
    return APIResponse.ok(data=[CommentResponse.from_domain(c) for c in comments])


@router.put(
    "/comments/{comment_id}",
    response_model=APIResponse[CommentResponse],
    tags=["Comments"],
    summary="댓글 수정 (작성자 본인/비회원 비밀번호/관리자)",
)
async def update_comment(
    comment_id: int,
    request: UpdateCommentRequest,
    role: RoleDep,
    member: MemberDep,
    comment_service: CommentServiceDep,
):
    comment = await comment_service.update_comment(
        comment_id=comment_id,
        content=request.content,
        requester_id=_requester_id(member),
        guest_password=request.guest_password,
        user_role=role,
    )
    return APIResponse.ok(data=CommentResponse.from_domain(comment))


@router.delete(
    "/comments/{comment_id}",
    response_model=APIResponse[None],
    tags=["Comments"],
    summary="댓글 삭제 (작성자 본인/비회원 비밀번호/관리자)",
)
async def delete_comment(
    comment_id: int,
    role: RoleDep,
    member: MemberDep,
    comment_service: CommentServiceDep,
    request: DeleteCommentRequest | None = None,
):
    await comment_service.delete_comment(
        comment_id=comment_id,
        requester_id=_requester_id(member),
        guest_password=request.guest_password if request else None,
        user_role=role,
    )
    return APIResponse.ok(message="댓글이 삭제되었습니다.")
