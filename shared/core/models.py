from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(UTC)


# 데이터베이스 테이블의 기준(베이스 클래스) 정의
class Base(DeclarativeBase):
    pass


class DateTimeBase:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=_utcnow,
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )


# 모델 초기화
def init_models():
    """SQLAlchemy 모델 메타데이터 등록"""
    import feature.auth.infrastructure.models  # 인증(토큰 블랙리스트)
    import feature.board.infrastructure.sqlalchemy.models  # 게시판
    import feature.user.infrastructure.models  # 회원


async def create_tables(engine: AsyncEngine) -> None:
    """등록된 모델 기준으로 없는 테이블만 생성 (기존 테이블·컬럼 변경은 반영하지 않음)"""
    init_models()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
