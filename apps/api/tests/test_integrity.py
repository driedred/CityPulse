from __future__ import annotations

from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.models import Issue, User
from app.models.enums import IssueStatus, UserRole


async def register_user(
    client: AsyncClient,
    *,
    email: str,
    full_name: str,
    password: str = "SecurePass123!",
) -> dict:
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "preferred_locale": "en",
        },
    )
    assert response.status_code == 201
    return response.json()


async def login_user(
    client: AsyncClient,
    *,
    email: str,
    password: str = "SecurePass123!",
) -> str:
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def create_admin_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str = "admin@example.com",
    password: str = "SecurePass123!",
) -> None:
    async with session_factory() as session:
        session.add(
            User(
                email=email,
                full_name="Admin User",
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
                preferred_locale="en",
            )
        )
        await session.commit()


async def publish_issue(
    session_factory: async_sessionmaker[AsyncSession],
    issue_id: str,
) -> None:
    async with session_factory() as session:
        issue = await session.scalar(select(Issue).where(Issue.id == UUID(issue_id)))
        assert issue is not None
        issue.status = IssueStatus.PUBLISHED
        await session.commit()


async def test_admin_integrity_detail_reflects_constructive_history(
    client: AsyncClient,
    seeded_category_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    citizen = await register_user(
        client,
        email="builder@example.com",
        full_name="Casey Builder",
    )
    await register_user(
        client,
        email="supporter@example.com",
        full_name="Jordan Supporter",
    )
    await create_admin_user(session_factory)

    citizen_token = await login_user(client, email="builder@example.com")
    supporter_token = await login_user(client, email="supporter@example.com")
    admin_token = await login_user(client, email="admin@example.com")

    create_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {citizen_token}"},
        json={
            "title": "Damaged sidewalk ramp near Central Library",
            "short_description": (
                "The curb ramp at the main library entrance is cracked and difficult "
                "to use with a stroller or wheelchair."
            ),
            "category_id": seeded_category_id,
            "latitude": 43.2389,
            "longitude": 76.8897,
            "source_locale": "en",
        },
    )
    assert create_response.status_code == 201
    issue_id = create_response.json()["id"]
    await publish_issue(session_factory, issue_id)

    feedback_response = await client.post(
        f"/api/public/issues/{issue_id}/feedback",
        headers={"Authorization": f"Bearer {supporter_token}"},
        json={"action": "support"},
    )
    assert feedback_response.status_code == 200

    integrity_response = await client.get(
        f"/api/admin/users/{citizen['id']}/integrity",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert integrity_response.status_code == 200
    body = integrity_response.json()
    assert body["trust_score"] > 60
    assert body["trust_weight_multiplier"] > 1
    assert body["abuse_risk_level"] == "low"
    assert any(
        factor["name"] == "approved_submissions" and factor["points"] > 0
        for factor in body["trust_factors"]
    )


async def test_duplicate_spam_attempts_trigger_submission_cooldown(
    client: AsyncClient,
    seeded_category_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_user(
        client,
        email="canonical@example.com",
        full_name="Original Reporter",
    )
    duplicate_user = await register_user(
        client,
        email="duplicate@example.com",
        full_name="Duplicate Reporter",
    )
    await create_admin_user(session_factory, email="integrity-admin@example.com")

    canonical_token = await login_user(client, email="canonical@example.com")
    duplicate_token = await login_user(client, email="duplicate@example.com")
    admin_token = await login_user(client, email="integrity-admin@example.com")

    canonical_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {canonical_token}"},
        json={
            "title": "Trash bins overflowing at Elm Park",
            "short_description": (
                "The bins on the north side of Elm Park are overflowing onto the path."
            ),
            "category_id": seeded_category_id,
            "latitude": 43.2391,
            "longitude": 76.8893,
            "source_locale": "en",
        },
    )
    assert canonical_response.status_code == 201

    duplicate_payload = {
        "title": "Trash bins overflowing at Elm Park",
        "short_description": (
            "The bins on the north side of Elm Park are overflowing onto the path."
        ),
        "category_id": seeded_category_id,
        "latitude": 43.2391,
        "longitude": 76.8893,
        "source_locale": "en",
    }

    first_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {duplicate_token}"},
        json=duplicate_payload,
    )
    second_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {duplicate_token}"},
        json=duplicate_payload,
    )
    third_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {duplicate_token}"},
        json=duplicate_payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert third_response.status_code == 429
    assert third_response.json()["error"]["code"] == "rate_limited"

    duplicate_integrity_response = await client.get(
        f"/api/admin/users/{duplicate_user['id']}/integrity",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert duplicate_integrity_response.status_code == 200
    duplicate_user_entry = duplicate_integrity_response.json()
    assert duplicate_user_entry["abuse_risk_level"] in {"medium", "high"}
    assert duplicate_user_entry["trust_weight_multiplier"] <= 1.05
    assert any(
        event["event_type"] == "duplicate_submission_attempt"
        for event in duplicate_user_entry["recent_events"]
    )


async def test_self_support_is_blocked_and_logged_for_admins(
    client: AsyncClient,
    seeded_category_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    self_user = await register_user(
        client,
        email="selfsupport@example.com",
        full_name="Self Supporter",
    )
    await create_admin_user(session_factory, email="self-admin@example.com")

    self_token = await login_user(client, email="selfsupport@example.com")
    admin_token = await login_user(client, email="self-admin@example.com")

    create_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {self_token}"},
        json={
            "title": "Street sign missing near Maple Avenue",
            "short_description": "The stop sign at Maple and 7th is missing after road work.",
            "category_id": seeded_category_id,
            "latitude": 43.2311,
            "longitude": 76.8812,
            "source_locale": "en",
        },
    )
    assert create_response.status_code == 201
    issue_id = create_response.json()["id"]
    await publish_issue(session_factory, issue_id)

    support_response = await client.post(
        f"/api/public/issues/{issue_id}/feedback",
        headers={"Authorization": f"Bearer {self_token}"},
        json={"action": "support"},
    )

    assert support_response.status_code == 409
    assert support_response.json()["error"]["code"] == "conflict"

    integrity_response = await client.get(
        f"/api/admin/users/{self_user['id']}/integrity",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert integrity_response.status_code == 200
    assert any(
        event["event_type"] == "self_support_blocked"
        for event in integrity_response.json()["recent_events"]
    )


async def test_rewrite_endpoint_rate_limits_authenticated_bursts(
    client: AsyncClient,
) -> None:
    await register_user(
        client,
        email="writer@example.com",
        full_name="Writer Person",
    )
    writer_token = await login_user(client, email="writer@example.com")
    headers = {"Authorization": f"Bearer {writer_token}"}

    for _ in range(6):
        response = await client.post(
            "/api/public/issues/rewrite",
            headers=headers,
            json={
                "title": "THIS IS TERRIBLE",
                "short_description": (
                    "This is a terrible mess and somebody has to fix it "
                    "immediately!!!"
                ),
            },
        )
        assert response.status_code == 200

    limited_response = await client.post(
        "/api/public/issues/rewrite",
        headers=headers,
        json={
            "title": "THIS IS TERRIBLE",
            "short_description": (
                "This is a terrible mess and somebody has to fix it immediately!!!"
            ),
        },
    )

    assert limited_response.status_code == 429
    assert limited_response.json()["error"]["code"] == "rate_limited"
