from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# auto_error=False: 인증 실패 응답을 APIResponse 포맷(401)으로 통일하기 위함
bearer_scheme = HTTPBearer(auto_error=False)

# 플레이스홀더 의존성에 선언하여 OpenAPI(Swagger) 문서에 Bearer 인증 요구를 노출한다.
# dependency_overrides 는 런타임에만 적용되므로, 선언이 없으면 Swagger 가 토큰을 보내지 않는다.
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
