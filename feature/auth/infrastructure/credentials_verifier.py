from uuid import UUID

from feature.auth.domain.service import UserCredentialVerifier
from feature.user.domain.repository import UserRepository
from feature.user.domain.service import PasswordHasher


class UserCredentialVerifierImpl(UserCredentialVerifier):
    # 미가입 이메일도 해시 검증 비용을 동일하게 소모시켜 계정 존재 여부 노출(타이밍 공격) 방지
    _dummy_hash: str | None = None

    def __init__(self, user_repo: UserRepository, password_hasher: PasswordHasher):
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    async def verify_credentials(self, email: str, plain_password: str) -> UUID | None:
        user = await self._user_repo.find_by_email(email)
        if not user:
            self._password_hasher.verify(plain_password, self._get_dummy_hash())
            return None

        if not self._password_hasher.verify(plain_password, user.password_hash):
            return None

        # 탈퇴 회원 로그인 차단
        if user.resign:
            return None

        return user.id

    def _get_dummy_hash(self) -> str:
        cls = type(self)
        if cls._dummy_hash is None:
            cls._dummy_hash = self._password_hasher.hash("timing-attack-dummy")
        return cls._dummy_hash
