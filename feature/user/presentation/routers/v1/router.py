import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from feature.user.application.service import UserService
from feature.user.domain.user import User
from feature.user.presentation.dependencies import (
    get_current_user,
    provide_user_service,
)
from feature.user.presentation.schemas import (
    ChangePasswordRequest,
    SignUpUserRequest,
    UserResponse,
)
from shared.core.exceptions import ForbiddenException
from shared.core.schemas import APIResponse

router = APIRouter(prefix="/v1/users", tags=["Users"])


@router.post(
    "",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="새로운 사용자를 등록합니다.",
)
async def sign_up(
    request: SignUpUserRequest,
    user_service: Annotated[UserService, Depends(provide_user_service)],
):
    """회원가입 엔드포인트"""
    user = await user_service.register_user(
        email=request.email,
        name=request.name,
        password=request.password,
    )
    response_data = UserResponse.model_validate(user)
    return APIResponse.ok(data=response_data, message="회원가입이 완료되었습니다.")


@router.patch(
    "/{user_id}/password",
    response_model=APIResponse[None],
    status_code=status.HTTP_200_OK,
    summary="비밀번호 변경",
    description="로그인한 본인의 비밀번호만 변경할 수 있습니다.",
)
async def change_password(
    user_id: uuid.UUID,
    request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(provide_user_service)],
):
    """비밀번호 변경 엔드포인트"""
    if current_user.id != user_id:
        raise ForbiddenException("본인의 비밀번호만 변경할 수 있습니다.")

    await user_service.change_password(
        user_id=user_id,
        old_password=request.old_password,
        new_password=request.new_password,
    )
    return APIResponse.ok(message="비밀번호가 성공적으로 변경되었습니다.")


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="내 정보 조회",
)
async def get_logged_user(user: Annotated[User, Depends(get_current_user)]):
    """로그인한 사용자 정보 조회"""
    return APIResponse.ok(data=UserResponse.model_validate(user))
