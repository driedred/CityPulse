from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Issue
from app.models.enums import IssueStatus


async def test_public_issue_feed_feedback_duplicate_and_rewrite(
    client: AsyncClient,
    seeded_category_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await client.post(
        "/api/auth/register",
        json={
            "email": "author@example.com",
            "password": "SecurePass123!",
            "full_name": "Alex Author",
            "preferred_locale": "en",
        },
    )
    await client.post(
        "/api/auth/register",
        json={
            "email": "supporter@example.com",
            "password": "SecurePass123!",
            "full_name": "Jamie Supporter",
            "preferred_locale": "en",
        },
    )

    author_login = await client.post(
        "/api/auth/login",
        json={"email": "author@example.com", "password": "SecurePass123!"},
    )
    author_headers = {
        "Authorization": f"Bearer {author_login.json()['access_token']}",
    }

    create_response = await client.post(
        "/api/issues",
        headers=author_headers,
        json={
            "title": "Overflowing trash near Elm Park",
            "short_description": (
                "Trash bins near Elm Park are overflowing and spreading "
                "waste onto the sidewalk."
            ),
            "category_id": seeded_category_id,
            "latitude": 43.2389,
            "longitude": 76.8897,
            "source_locale": "en",
        },
    )
    issue_id = create_response.json()["id"]

    async with session_factory() as session:
        issue = await session.scalar(select(Issue).where(Issue.id == UUID(issue_id)))
        assert issue is not None
        issue.status = IssueStatus.PUBLISHED
        await session.commit()

    supporter_login = await client.post(
        "/api/auth/login",
        json={"email": "supporter@example.com", "password": "SecurePass123!"},
    )
    supporter_headers = {
        "Authorization": f"Bearer {supporter_login.json()['access_token']}",
    }

    feedback_response = await client.post(
        f"/api/public/issues/{issue_id}/feedback",
        headers=supporter_headers,
        json={"action": "support"},
    )

    assert feedback_response.status_code == 200
    assert feedback_response.json()["support_count"] == 1

    feed_response = await client.get("/api/public/issues?sort=top")

    assert feed_response.status_code == 200
    feed_body = feed_response.json()
    assert len(feed_body) == 1
    assert feed_body[0]["support_count"] == 1
    assert feed_body[0]["importance_label"] is not None

    duplicate_response = await client.post(
        "/api/public/issues/duplicates",
        json={
            "title": "Overflowing trash close to Elm Park",
            "short_description": "Bins near the park are overflowing onto the pavement again.",
            "category_id": seeded_category_id,
            "latitude": 43.2391,
            "longitude": 76.8895,
        },
    )

    assert duplicate_response.status_code == 200
    duplicate_body = duplicate_response.json()
    assert duplicate_body["status"] in {
        "possible_duplicates",
        "high_confidence_duplicate",
    }
    assert duplicate_body["matches"]
    assert duplicate_body["matches"][0]["issue"]["id"] == issue_id

    rewrite_response = await client.post(
        "/api/public/issues/rewrite",
        json={
            "title": "TRASH EVERYWHERE!!!",
            "short_description": (
                "This area is a disgusting mess and someone needs to fix it "
                "asap!!!"
            ),
        },
    )

    assert rewrite_response.status_code == 200
    rewrite_body = rewrite_response.json()
    assert "Please review this location when possible." in rewrite_body["rewritten_description"]
