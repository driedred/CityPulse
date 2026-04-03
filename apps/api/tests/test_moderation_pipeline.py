from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole
from app.schemas.issue import (
    AIRewriteStructuredResponse,
    DeterministicModerationDecision,
    IssueRewriteRequest,
    ModerationReasonRead,
)
from app.services.ai_rewrite import AIRewriteService
from app.services.llm_moderation import LLMModerationService
from app.services.moderation_models import ModerationSubmission
from app.services.openai_client import AIServiceError


class FailingStructuredClient:
    async def generate_structured_output(self, **kwargs):
        del kwargs
        raise AIServiceError("service unavailable")


class FakeStructuredClient:
    def __init__(self, response) -> None:
        self.response = response

    async def generate_structured_output(self, **kwargs):
        del kwargs
        return self.response


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
    email: str = "moderation-admin@example.com",
    password: str = "SecurePass123!",
) -> None:
    async with session_factory() as session:
        session.add(
            User(
                email=email,
                full_name="Moderation Admin",
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
                preferred_locale="en",
            )
        )
        await session.commit()


async def test_issue_submission_can_be_rejected_by_deterministic_moderation(
    client: AsyncClient,
    seeded_category_id: str,
) -> None:
    token = await _register_and_login(
        client,
        email="rejected-reporter@example.com",
        full_name="Rejected Reporter",
    )

    response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "USELESS IDIOTS WON'T FIX THIS!!!",
            "short_description": (
                "Those people don't belong here and these useless idiots never fix "
                "anything at this location."
            ),
            "category_id": seeded_category_id,
            "latitude": 43.2389,
            "longitude": 76.8897,
            "source_locale": "en",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "rejected"
    assert body["moderation_state"] == "completed"
    assert body["latest_moderation"]["layer"] == "deterministic"
    assert body["latest_moderation"]["decision_code"] == "reject"
    assert "focus on the civic issue" in body["latest_moderation"]["user_safe_explanation"]


async def test_admin_moderation_endpoints_expose_audit_and_rerun(
    client: AsyncClient,
    seeded_category_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    citizen_token = await _register_and_login(
        client,
        email="moderation-citizen@example.com",
        full_name="Moderation Citizen",
    )

    create_response = await client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {citizen_token}"},
        json={
            "title": "Broken bus shelter on Pine Avenue",
            "short_description": (
                "The shelter roof is damaged and riders are standing in rain near Pine Avenue."
            ),
            "category_id": seeded_category_id,
            "latitude": 43.24,
            "longitude": 76.89,
            "source_locale": "en",
        },
    )
    issue_id = UUID(create_response.json()["id"])

    await _create_admin_user(session_factory)
    admin_login = await client.post(
        "/api/auth/login",
        json={"email": "moderation-admin@example.com", "password": "SecurePass123!"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    list_response = await client.get("/api/admin/moderation/issues", headers=admin_headers)
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert any(item["id"] == str(issue_id) for item in list_body)

    detail_response = await client.get(
        f"/api/admin/moderation/issues/{issue_id}",
        headers=admin_headers,
    )
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    layers = {result["layer"] for result in detail_body["results"]}
    assert {"deterministic", "llm"} <= layers

    rerun_response = await client.post(
        f"/api/admin/moderation/issues/{issue_id}/rerun",
        headers=admin_headers,
    )
    assert rerun_response.status_code == 200
    rerun_body = rerun_response.json()
    assert len(rerun_body["results"]) >= 4


async def test_llm_moderation_service_falls_back_when_openai_unavailable() -> None:
    submission = ModerationSubmission(
        issue_id=UUID("11111111-1111-1111-1111-111111111111"),
        author_id=UUID("22222222-2222-2222-2222-222222222222"),
        title="THIS STOP IS A MESS!!!",
        short_description=(
            "The bus stop shelter is damaged and people are waiting outside in bad weather."
        ),
        category_slug="transport",
        source_locale="en",
        latitude=43.24,
        longitude=76.89,
    )
    deterministic = DeterministicModerationDecision(
        outcome="needs_manual_review",
        confidence=0.7,
        summary="Flagged for caps.",
        user_safe_explanation="Needs a quick review.",
        internal_notes="Caps-heavy wording.",
        machine_reasons=[
            ModerationReasonRead(
                code="excessive_caps",
                label="Too much caps emphasis",
                severity="medium",
            )
        ],
        flags={"caps_ratio": 0.5},
        escalation_required=True,
    )

    decision = await LLMModerationService(client=FailingStructuredClient()).review(
        submission,
        deterministic,
        allowed_category_slugs={"transport", "roads"},
    )

    assert decision.outcome == "needs_manual_review"
    assert decision.flags["fallback"] is True
    assert decision.escalation_required is True


async def test_ai_rewrite_service_accepts_structured_openai_output() -> None:
    service = AIRewriteService(
        client=FakeStructuredClient(
            AIRewriteStructuredResponse(
                rewritten_title="Damaged bus shelter on Pine Avenue",
                rewritten_description=(
                    "The bus shelter roof appears damaged and riders are exposed to rain. "
                    "Please inspect the stop and repair the shelter."
                ),
                explanation="Reduced accusatory tone and clarified the request.",
                tone_classification="frustrated",
            )
        )
    )

    response = await service.rewrite(
        IssueRewriteRequest(
            title="Why won't anyone fix this bus stop?",
            short_description="This stop is awful and nobody ever helps.",
            category_id=None,
            source_locale="en",
            context_hint="Transit shelter",
        ),
        category_slug="transport",
    )

    assert response.rewritten_title == "Damaged bus shelter on Pine Avenue"
    assert "clarified the request" in response.explanation
    assert response.tone_classification == "frustrated"
