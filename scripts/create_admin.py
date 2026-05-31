"""CLI script to create an admin user."""

import asyncio
import getpass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import get_settings
from app.models.base import Base  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.models.user import User
from app.repositories.user import UserRepository


async def _create(name: str, password: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_name(name)
        if existing:
            print(f"User '{name}' already exists.")
            return
        user = User()
        user.name = name
        user.set_password(password)
        user.authenticated = 1
        session.add(user)
        await session.commit()
        print(f"Admin user '{name}' created successfully.")

    await engine.dispose()


def main() -> None:
    name = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        return
    asyncio.run(_create(name, password))


if __name__ == "__main__":
    main()
