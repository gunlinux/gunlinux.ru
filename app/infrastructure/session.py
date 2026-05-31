from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.core.settings import get_settings


def _make_engine():
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)


engine = _make_engine()
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

_WROTE_FLAG = "wrote"


@event.listens_for(Session, "after_flush")
def _mark_wrote(  # pyright: ignore[reportUnusedFunction]
    session: Session,
    flush_context: object,  # pyright: ignore[reportUnusedParameter]
) -> None:
    # Fires only when a flush actually emits INSERT/UPDATE/DELETE, so it marks
    # the unit of work as a writer. Pure reads never flush, so the flag stays
    # unset and get_db can skip the COMMIT.
    session.info[_WROTE_FLAG] = True


def _has_pending_writes(session: AsyncSession) -> bool:
    sync = session.sync_session
    return bool(sync.info.get(_WROTE_FLAG) or sync.new or sync.dirty or sync.deleted)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            if _has_pending_writes(session):
                await session.commit()
        except Exception:
            await session.rollback()
            raise
