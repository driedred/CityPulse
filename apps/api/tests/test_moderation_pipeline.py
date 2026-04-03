from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole
from app.schemas.issue import (
    AIImageModerationStructuredResponse,
    AIRewriteStructuredResponse,
    DeterministicModerationDecision,
    IssueRewriteRequest,
    ModerationReasonRead,
)
from app.services.ai_rewrite import AIRewriteService
from app.services.image_moderation import ImageModerationService
from app.services.llm_moderation import LLMModerationService
from app.services.moderation_models import (
    ModerationAttachmentDescriptor,
    ModerationSubmission,
)
from app.services.openai_client import AIServiceError


class FailingStructuredClient:
    def __init__(self, raw_output: str | None = None) -> None:
        self.raw_output = raw_output

    async def generate_structured_output(self, **kwargs):
        del kwargs
        raise AIServiceError("service unavailable", raw_output=self.raw_output)


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


async def test_image_moderation_service_rejects_explicit_visual_content() -> None:
    service = ImageModerationService(
        client=FakeStructuredClient(
            AIImageModerationStructuredResponse(
                outcome="reject",
                confidence=0.97,
                summary="The image contains explicit nudity.",
                user_safe_explanation="The attached photo cannot be accepted.",
                internal_notes="Visible genital content detected in the uploaded image.",
                machine_reasons=[
                    ModerationReasonRead(
                        code="explicit_nudity_detected",
                        label="Visible genitals or explicit nudity were detected.",
                        severity="high",
                    )
                ],
                matches_issue=False,
                relevance_score=0.04,
                contains_explicit_nudity=True,
                contains_graphic_violence=False,
                flags={"policy_bucket": "sexual_content"},
            )
        )
    )

    submission = ModerationSubmission(
        issue_id=UUID("11111111-1111-1111-1111-111111111111"),
        author_id=UUID("22222222-2222-2222-2222-222222222222"),
        title="Unsafe graffiti on public wall",
        short_description="An explicit image was painted on a wall near the school.",
        category_slug="safety",
        source_locale="en",
        latitude=43.24,
        longitude=76.89,
        attachments=(
            ModerationAttachmentDescriptor(
                original_filename="wall-photo.jpg",
                content_type="image/jpeg",
                size_bytes=1024,
                moderation_image_url="data:image/jpeg;base64,AAAA",
            ),
        ),
    )

    decision = await service.review(submission)

    assert decision is not None
    assert decision.outcome == "reject"
    assert decision.flags["image_reviewed"] is True
    assert any(reason.code == "explicit_nudity_detected" for reason in decision.machine_reasons)


async def test_image_moderation_service_escalates_context_mismatch() -> None:
    service = ImageModerationService(
        client=FakeStructuredClient(
            AIImageModerationStructuredResponse(
                outcome="approve",
                confidence=0.74,
                summary="The image is not overtly unsafe.",
                user_safe_explanation="The attached photo needs a quick review.",
                internal_notes="The image appears to show an unrelated indoor portrait.",
                machine_reasons=[],
                matches_issue=False,
                relevance_score=0.09,
                contains_explicit_nudity=False,
                contains_graphic_violence=False,
                flags={"detected_scene": "portrait"},
            )
        )
    )

    submission = ModerationSubmission(
        issue_id=UUID("33333333-3333-3333-3333-333333333333"),
        author_id=UUID("44444444-4444-4444-4444-444444444444"),
        title="Blocked storm drain on Oak Street",
        short_description="The storm drain is clogged after rain and water is pooling.",
        category_slug="roads",
        source_locale="en",
        latitude=43.22,
        longitude=76.91,
        attachments=(
            ModerationAttachmentDescriptor(
                original_filename="portrait.jpg",
                content_type="image/jpeg",
                size_bytes=2048,
                moderation_image_url="data:image/jpeg;base64,BBBB",
            ),
        ),
    )

    decision = await service.review(submission)

    assert decision is not None
    assert decision.outcome == "needs_manual_review"
    assert any(reason.code == "image_context_mismatch" for reason in decision.machine_reasons)


async def test_image_moderation_service_blocks_refusal_like_model_output() -> None:
    service = ImageModerationService(
        client=FailingStructuredClient(raw_output="I can't help with that request.")
    )

    submission = ModerationSubmission(
        issue_id=UUID("55555555-5555-5555-5555-555555555555"),
        author_id=UUID("66666666-6666-6666-6666-666666666666"),
        title="Broken park light",
        short_description="The park light has failed and the path is dark at night.",
        category_slug="lighting",
        source_locale="en",
        latitude=43.21,
        longitude=76.87,
        attachments=(
            ModerationAttachmentDescriptor(
                original_filename="night-photo.jpg",
                content_type="image/jpeg",
                size_bytes=4096,
                moderation_image_url="data:image/jpeg;base64,CCCC",
            ),
        ),
    )

    decision = await service.review(submission)

    assert decision is not None
    assert decision.outcome == "reject"
    assert decision.flags["fallback"] is True
    assert any(
        reason.code == "image_model_refusal_sensitive_content"
        for reason in decision.machine_reasons
    )


async def test_attachment_metadata_can_reject_issue_after_initial_submit(
    client: AsyncClient,
    seeded_category_id: str,
) -> None:
    token = await _register_and_login(
        client,
        email="image-attachment@example.com",
        full_name="Image Attachment",
    )
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/issues",
        headers=headers,
        json={
            "title": "Broken playground bench",
            "short_description": "The wooden bench near the playground is broken and splintered.",
            "category_id": seeded_category_id,
            "latitude": 43.2389,
            "longitude": 76.8897,
            "source_locale": "en",
        },
    )

    assert create_response.status_code == 201
    issue_id = create_response.json()["id"]
    assert create_response.json()["status"] == "approved"

    attachment_response = await client.post(
        f"/api/issues/{issue_id}/attachments",
        headers=headers,
        json={
            "original_filename": "public-penis-photo.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 8192,
            "storage_key": f"issues/{issue_id}/public-penis-photo.jpg",
        },
    )

    assert attachment_response.status_code == 201

    issue_response = await client.get(f"/api/issues/{issue_id}", headers=headers)

    assert issue_response.status_code == 200
    issue_body = issue_response.json()
    assert issue_body["status"] == "rejected"
    assert issue_body["latest_moderation"]["decision_code"] == "reject"
    assert issue_body["latest_moderation"]["layer"] == "deterministic"
