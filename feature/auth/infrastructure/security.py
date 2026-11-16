import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from auth.domain.entities import TokenPayload
from auth.domain.service import TokenProvider


class JwtTokenProvider(TokenProvider):
    def __init__(
        self,
        secret_key: str = os.getenv("JWT_SECRET_KEY", ""),
        algorithm: str = "HS512",
        access_token_expire_minutes: int = 60,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = access_token_expire_minutes

    def create_access_token(self, user_id: uuid.UUID) -> tuple[str, str, datetime, int]:
        now = datetime.now(UTC)
        expires_delta = timedelta(minutes=self.expire_minutes)
        expired_at = now + expires_delta
        expires_in = int(expires_delta.total_seconds())

        jti = str(uuid.uuid4())

        payload = {"sub": str(user_id), "jti": jti, "exp": expired_at, "iat": now}

        encoded_jwt = jwt.encode(payload, self.secret_key, self.algorithm)
        return encoded_jwt, jti, expired_at, expires_in

    def decode_token(self, token: str) -> TokenPayload:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        return TokenPayload(
            user_id=uuid.UUID(payload["sub"]),
            jti=payload["jti"],
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
