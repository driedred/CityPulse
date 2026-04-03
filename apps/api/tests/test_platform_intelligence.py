from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.models import Issue, IssueDuplicateLink, ModerationResult, User
from app.models.enums import IssueStatus, ModerationResultStatus, UserRole


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    full_name: str,
    password: str = "SecurePass123!",
) -> str:
    await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "preferred_locale": "en",
        },
    )
    login_response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    return login_response.json()["access_token"]


async def _create_admin_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str = "admin@example.com",
    password: str = "SecurePass123!",
) -> None:
    async with session_factory() as session:
        session.add(
            User(
                email=email,
                full_name="Admin Operator",
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
                preferred_locale="en",
            )
        )
        await session.commit()


async def test_impact_score_public_and_admin_endpoints(
    client: AsyncClient,
    seeded_category_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    author_token = await _register_and_login(
        client,
        email="impact-author@example.com",
        full_name="Impact Author",
    )
    supporter_token = await _register_and_login(
        client,
        email="impact-supporter@example.com",
        full_name="Impact Supporter",
    )

    create_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {author_token}"},
        json={
            "title": "Unsafe crossing near the elementary school",
            "short_description": (
                "Cars are speeding through the crossing and the painted markings "
                "are almost gone."
            ),
            "category_id": seeded_category_id,
            "latitude": 43.2389,
            "longitude": 76.8897,
            "source_locale": "en",
        },
    )
    issue_id = UUID(create_response.json()["id"])

    async with session_factory() as session:
        issue = await session.scalar(select(Issue).where(Issue.id == issue_id))
        assert issue is not None
        issue.status = IssueStatus.PUBLISHED
        session.add(
            ModerationResult(
                issue_id=issue.id,
                status=ModerationResultStatus.APPROVED,
                provider_name="local-test",
                model_name="impact-check",
                confidence=0.91,
                summary="High-quality civic report.",
            )
        )
        await session.commit()

    feedback_response = await client.post(
        f"/api/public/issues/{issue_id}/feedback",
        headers={"Authorization": f"Bearer {supporter_token}"},
        json={"action": "support"},
    )
    assert feedback_response.status_code == 200
    assert feedback_response.json()["public_impact_score"] is not None

    public_response = await client.get(f"/api/public/issues/{issue_id}/impact")
    assert public_response.status_code == 200
    public_body = public_response.json()
    assert public_body["public_impact_score"] > 0
    assert public_body["affected_people_estimate"] >= 25
    assert public_body["importance_label"]

    await _create_admin_user(session_factory)
    admin_login = await client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "SecurePass123!"},
    )
    admin_token = admin_login.json()["access_token"]

    admin_response = await client.get(
        f"/api/issues/{issue_id}/impact/admin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_response.status_code == 200
    admin_body = admin_response.json()
    factor_names = {factor["name"] for factor in admin_body["factors"]}
    assert "unique_supporters" in factor_names
    assert "local_density" in factor_names
    assert "moderation_quality" in factor_names


async def test_duplicate_detection_returns_high_confidence_match(
    client: AsyncClient,
    seeded_category_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    author_token = await _register_and_login(
        client,
        email="duplicate-author@example.com",
        full_name="Duplicate Author",
    )

    create_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {author_token}"},
        json={
            "title": "Overflowing trash near River Street",
            "short_description": (
                "Trash bins near River Street are overflowing and waste is spreading "
                "onto the sidewalk."
            ),
            "category_id": seeded_category_id,
            "latitude": 43.2389,
            "longitude": 76.8897,
            "source_locale": "en",
        },
    )
    issue_id = UUID(create_response.json()["id"])

    async with session_factory() as session:
        issue = await session.scalar(select(Issue).where(Issue.id == issue_id))
        assert issue is not None
        issue.status = IssueStatus.PUBLISHED
        await session.commit()

    duplicate_response = await client.post(
        "/api/public/issues/duplicates",
        json={
            "title": "Overflowing trash on River Street",
            "short_description": (
                "Bins on River Street are overflowing and trash is spilling onto the "
                "walkway."
            ),
            "category_id": seeded_category_id,
            "latitude": 43.2390,
            "longitude": 76.8898,
            "image_hashes": [],
        },
    )
    assert duplicate_response.status_code == 200
    duplicate_body = duplicate_response.json()
    assert duplicate_body["status"] == "high_confidence_duplicate"
    assert duplicate_body["matches"]
    top_match = duplicate_body["matches"][0]
    assert top_match["existing_issue_id"] == str(issue_id)
    assert top_match["recommended_action"] == "support_existing"
    assert top_match["category_match"] is True
    assert top_match["distance_km"] < 0.35
    assert top_match["text_similarity"] >= 0.5


async def test_support_existing_issue_prevents_double_count_and_tracks_duplicate_signal(
    client: AsyncClient,
    seeded_category_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    author_token = await _register_and_login(
        client,
        email="support-author@example.com",
        full_name="Support Author",
    )
    supporter_token = await _register_and_login(
        client,
        email="support-citizen@example.com",
        full_name="Support Citizen",
    )

    create_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {author_token}"},
        json={
            "title": "Damaged bus shelter on Market Avenue",
            "short_description": (
                "The bus shelter glass is cracked and people are waiting in an unsafe "
                "space."
            ),
            "category_id": seeded_category_id,
            "latitude": 43.24,
            "longitude": 76.89,
            "source_locale": "en",
        },
    )
    issue_id = UUID(create_response.json()["id"])

    async with session_factory() as session:
        issue = await session.scalar(select(Issue).where(Issue.id == issue_id))
        assert issue is not None
        issue.status = IssueStatus.PUBLISHED
        await session.commit()

    payload = {
        "candidate_title": "Broken shelter on Market Avenue",
        "candidate_description": "Glass panels are broken and riders are exposed.",
        "candidate_category_id": seeded_category_id,
        "candidate_latitude": 43.2401,
        "candidate_longitude": 76.8901,
        "similarity_score": 0.82,
        "distance_km": 0.11,
        "text_similarity": 0.74,
        "category_match": True,
        "reason_breakdown": ["Same category", "Nearly identical location"],
        "image_hashes": [],
    }

    first_support = await client.post(
        f"/api/public/issues/{issue_id}/support",
        headers={"Authorization": f"Bearer {supporter_token}"},
        json=payload,
    )
    assert first_support.status_code == 200
    first_body = first_support.json()
    assert first_body["support_changed"] is True
    assert first_body["support_count"] == 1
    assert first_body["duplicate_link_id"] is not None

    second_support = await client.post(
        f"/api/public/issues/{issue_id}/support",
        headers={"Authorization": f"Bearer {supporter_token}"},
        json=payload,
    )
    assert second_support.status_code == 200
    second_body = second_support.json()
    assert second_body["support_changed"] is False
    assert second_body["support_count"] == 1

    async with session_factory() as session:
        duplicate_links = (
            await session.scalars(
                select(IssueDuplicateLink).where(
                    IssueDuplicateLink.canonical_issue_id == issue_id
                )
            )
        ).all()
        assert duplicate_links
