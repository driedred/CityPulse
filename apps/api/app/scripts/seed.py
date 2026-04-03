from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models import IssueCategory, User
from app.models.enums import UserRole

DEFAULT_CATEGORIES = [
    {
        "slug": "roads",
        "display_name": "Roads",
        "description": "Potholes, damaged surfaces, and road safety issues.",
    },
    {
        "slug": "sanitation",
        "display_name": "Sanitation",
        "description": "Garbage, dumping, and public cleanliness concerns.",
    },
    {
        "slug": "lighting",
        "display_name": "Lighting",
        "description": "Streetlight outages and dark public areas.",
    },
    {
        "slug": "safety",
        "display_name": "Safety",
        "description": "Hazards, public safety risks, and dangerous infrastructure.",
    },
    {
        "slug": "transport",
        "display_name": "Transport",
        "description": "Bus stops, transit access, and street mobility issues.",
    },
]


async def seed_categories_in_session(session: AsyncSession) -> int:
    existing_slugs = set(
        (
            await session.scalars(
                select(IssueCategory.slug).where(
                    IssueCategory.slug.in_([item["slug"] for item in DEFAULT_CATEGORIES])
                )
            )
        ).all()
    )

    created_count = 0
    for category in DEFAULT_CATEGORIES:
        if category["slug"] in existing_slugs:
            continue

        session.add(IssueCategory(**category))
        created_count += 1

    return created_count


async def seed_categories() -> int:
    created_count = 0

    async with AsyncSessionLocal() as session:
        created_count = await seed_categories_in_session(session)
        await session.commit()

    return created_count


async def seed_default_admin_in_session(
    session: AsyncSession,
    settings: Settings,
) -> bool:
    existing_admin = await session.scalar(
        select(User).where(User.email == settings.default_admin_email.lower())
    )

    if existing_admin is not None:
        return False

    admin = User(
        email=settings.default_admin_email.lower(),
        full_name=settings.default_admin_full_name,
        hashed_password=hash_password(settings.default_admin_password),
        role=UserRole.ADMIN,
        preferred_locale="en",
    )
    session.add(admin)
    return True


async def seed_default_admin(settings: Settings) -> bool:
    async with AsyncSessionLocal() as session:
        created = await seed_default_admin_in_session(session, settings)
        await session.commit()
        return created


async def main() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        categories_created = await seed_categories_in_session(session)
        admin_created = await seed_default_admin_in_session(session, settings)
        await session.commit()

    print(f"Seeded categories: {categories_created}")
    print(f"Default admin created: {admin_created}")


if __name__ == "__main__":
    asyncio.run(main())
