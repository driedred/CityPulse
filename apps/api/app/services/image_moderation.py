from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.issue import (
    AIImageModerationStructuredResponse,
    LLMModerationDecision,
    ModerationReasonRead,
)
from app.services.moderation_models import (
    ModerationAttachmentDescriptor,
    ModerationSubmission,
)
from app.services.openai_client import AIServiceError, OpenAIResponsesClient
from app.services.prompt_templates import (
    build_image_moderation_system_prompt,
    build_image_moderation_user_content,
)


@dataclass(frozen=True)
class ImageModerationThresholds:
    mismatch_review_threshold: float = 0.42
    mismatch_strong_threshold: float = 0.18


@dataclass(frozen=True)
class ImageModerationConfig:
    explicit_filename_terms: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "nude",
                "nudity",
                "naked",
                "penis",
                "vagina",
                "porn",
                "sex",
                "xxx",
                "genital",
                "dick",
                "boobs",
            }
        )
    )
    graphic_filename_terms: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "gore",
                "dismember",
                "dismembered",
                "corpse",
                "bloodbath",
                "beheaded",
                "decapitated",
                "mutilated",
                "severed",
            }
        )
    )
    refusal_markers: tuple[str, ...] = (
        "i can't help",
        "i cannot help",
        "i can't assist",
        "i cannot assist",
        "unable to help",
        "not able to help",
        "cannot comply",
        "can't comply",
    )
    thresholds: ImageModerationThresholds = field(default_factory=ImageModerationThresholds)


class ImageModerationService:
    def __init__(
        self,
        *,
        client: OpenAIResponsesClient | None = None,
        config: ImageModerationConfig | None = None,
    ) -> None:
        self.client = client or OpenAIResponsesClient()
        self.config = config or ImageModerationConfig()

    async def review(
        self,
        submission: ModerationSubmission,
    ) -> LLMModerationDecision | None:
        if not submission.attachments:
            return None

        attachment_decisions: list[
            tuple[ModerationAttachmentDescriptor, LLMModerationDecision]
        ] = []

        for attachment in submission.attachments:
            decision = await self._review_attachment(submission, attachment)
            attachment_decisions.append((attachment, decision))
            if decision.outcome == "reject":
                break

        return self._aggregate_attachment_decisions(attachment_decisions)

    async def _review_attachment(
        self,
        submission: ModerationSubmission,
        attachment: ModerationAttachmentDescriptor,
    ) -> LLMModerationDecision:
        filename_decision = self._review_filename(attachment)
        if filename_decision is not None:
            return filename_decision

        content_type = attachment.content_type.lower().strip()
        if not content_type.startswith("image/"):
            return self._build_decision(
                outcome="reject",
                confidence=0.95,
                summary="Image moderation rejected a non-image attachment.",
                user_safe_explanation=(
                    "Only issue photos are accepted in this upload step. Please attach a photo "
                    "that documents the issue."
                ),
                internal_notes=(
                    "Attachment content type did not start with image/ and was rejected by "
                    "image moderation."
                ),
                machine_reasons=[
                    ModerationReasonRead(
                        code="unsupported_attachment_type",
                        label="The attachment is not an image file.",
                        severity="high",
                        evidence=attachment.content_type,
                    )
                ],
                flags={
                    "fallback": True,
                    "image_reviewed": False,
                    "source": "content-type-guard",
                    "attachment_filename": attachment.original_filename,
                },
            )

        if not attachment.moderation_image_url:
            return self._build_decision(
                outcome="needs_manual_review",
                confidence=0.61,
                summary=(
                    "Image moderation needs manual review because no visual preview "
                    "was available."
                ),
                user_safe_explanation=(
                    "One attached photo needs a quick human review before the report can move "
                    "forward."
                ),
                internal_notes=(
                    "Attachment included image metadata but no moderation_image_url preview. "
                    "Automatic visual review could not run."
                ),
                machine_reasons=[
                    ModerationReasonRead(
                        code="image_visual_input_unavailable",
                        label="Automatic visual moderation could not access the uploaded image.",
                        severity="medium",
                        evidence=attachment.original_filename,
                    )
                ],
                flags={
                    "fallback": True,
                    "image_reviewed": False,
                    "source": "missing-visual-preview",
                    "attachment_filename": attachment.original_filename,
                },
                escalation_required=True,
            )

        try:
            structured = await self.client.generate_structured_output(
                schema_name="citypulse_image_moderation",
                schema_model=AIImageModerationStructuredResponse,
                system_prompt=build_image_moderation_system_prompt(),
                user_content=build_image_moderation_user_content(submission, attachment),
                max_output_tokens=800,
            )
            return self._decision_from_structured(attachment, structured)
        except AIServiceError as exc:
            return self._fallback_from_error(attachment, exc)

    def _review_filename(
        self,
        attachment: ModerationAttachmentDescriptor,
    ) -> LLMModerationDecision | None:
        lowered = attachment.original_filename.lower()

        explicit_hits = sorted(
            term for term in self.config.explicit_filename_terms if term in lowered
        )
        if explicit_hits:
            return self._build_decision(
                outcome="reject",
                confidence=0.96,
                summary=(
                    "Image moderation rejected the attachment based on explicit "
                    "sexual indicators."
                ),
                user_safe_explanation=(
                    "This photo cannot be accepted because it appears to include explicit sexual "
                    "content or visible genital content."
                ),
                internal_notes=(
                    "Attachment filename triggered explicit sexual-content indicators before "
                    "model-based review."
                ),
                machine_reasons=[
                    ModerationReasonRead(
                        code="explicit_attachment_filename",
                        label="The attachment filename strongly suggests explicit sexual content.",
                        severity="high",
                        evidence=", ".join(explicit_hits),
                    )
                ],
                flags={
                    "fallback": True,
                    "image_reviewed": False,
                    "source": "filename-heuristic",
                    "explicit_hits": explicit_hits,
                    "attachment_filename": attachment.original_filename,
                },
            )

        graphic_hits = sorted(
            term for term in self.config.graphic_filename_terms if term in lowered
        )
        if graphic_hits:
            return self._build_decision(
                outcome="reject",
                confidence=0.95,
                summary=(
                    "Image moderation rejected the attachment based on graphic "
                    "violence indicators."
                ),
                user_safe_explanation=(
                    "This photo cannot be accepted because it appears to include graphic injury "
                    "or dismemberment."
                ),
                internal_notes=(
                    "Attachment filename triggered graphic violence indicators before model-based "
                    "review."
                ),
                machine_reasons=[
                    ModerationReasonRead(
                        code="graphic_attachment_filename",
                        label="The attachment filename strongly suggests graphic violence or gore.",
                        severity="high",
                        evidence=", ".join(graphic_hits),
                    )
                ],
                flags={
                    "fallback": True,
                    "image_reviewed": False,
                    "source": "filename-heuristic",
                    "graphic_hits": graphic_hits,
                    "attachment_filename": attachment.original_filename,
                },
            )

        return None

    def _decision_from_structured(
        self,
        attachment: ModerationAttachmentDescriptor,
        structured: AIImageModerationStructuredResponse,
    ) -> LLMModerationDecision:
        reasons = list(structured.machine_reasons)
        outcome = structured.outcome

        if structured.contains_explicit_nudity:
            reasons.append(
                ModerationReasonRead(
                    code="explicit_nudity_detected",
                    label="Visible genitals or explicit nudity were detected.",
                    severity="high",
                    evidence=attachment.original_filename,
                )
            )
        if structured.contains_graphic_violence:
            reasons.append(
                ModerationReasonRead(
                    code="graphic_violence_detected",
                    label="Graphic injury, gore, or dismemberment were detected.",
                    severity="high",
                    evidence=attachment.original_filename,
                )
            )

        if structured.contains_explicit_nudity or structured.contains_graphic_violence:
            outcome = "reject"

        if outcome == "approve" and (
            not structured.matches_issue
            or structured.relevance_score < self.config.thresholds.mismatch_review_threshold
        ):
            outcome = "needs_manual_review"
            reasons.append(
                ModerationReasonRead(
                    code="image_context_mismatch",
                    label="The image does not clearly match the reported civic issue.",
                    severity=(
                        "high"
                        if structured.relevance_score
                        < self.config.thresholds.mismatch_strong_threshold
                        else "medium"
                    ),
                    evidence=attachment.original_filename,
                )
            )

        return self._build_decision(
            outcome=outcome,
            confidence=structured.confidence,
            summary=structured.summary,
            user_safe_explanation=structured.user_safe_explanation,
            internal_notes=structured.internal_notes,
            machine_reasons=self._deduplicate_reasons(reasons),
            flags={
                **structured.flags,
                "image_reviewed": True,
                "source": "openai-image-review",
                "attachment_filename": attachment.original_filename,
                "matches_issue": structured.matches_issue,
                "relevance_score": structured.relevance_score,
                "contains_explicit_nudity": structured.contains_explicit_nudity,
                "contains_graphic_violence": structured.contains_graphic_violence,
            },
            escalation_required=outcome == "needs_manual_review",
        )

    def _fallback_from_error(
        self,
        attachment: ModerationAttachmentDescriptor,
        error: AIServiceError,
    ) -> LLMModerationDecision:
        raw_output = (error.raw_output or "").strip()
        if self._looks_like_refusal(raw_output):
            return self._build_decision(
                outcome="reject",
                confidence=0.81,
                summary=(
                    "Image moderation rejected the attachment after a safety refusal "
                    "from the model."
                ),
                user_safe_explanation=(
                    "One attached photo cannot be accepted automatically because it appears to "
                    "contain unsafe or clearly inappropriate visual content."
                ),
                internal_notes=(
                    "The multimodal moderation request returned refusal-like text instead of the "
                    "expected schema. This is treated as a sensitive-image block."
                ),
                machine_reasons=[
                    ModerationReasonRead(
                        code="image_model_refusal_sensitive_content",
                        label="The image review model refused the visual moderation request.",
                        severity="high",
                        evidence=raw_output[:160] or attachment.original_filename,
                    )
                ],
                flags={
                    "fallback": True,
                    "image_reviewed": False,
                    "source": "openai-refusal-fallback",
                    "attachment_filename": attachment.original_filename,
                },
            )

        return self._build_decision(
            outcome="needs_manual_review",
            confidence=0.58,
            summary="Image moderation could not reach a structured decision.",
            user_safe_explanation=(
                "One attached photo needs a quick human review before the report can move forward."
            ),
            internal_notes=(
                "The image moderation request failed or returned unstructured output, so the "
                "attachment was escalated instead of being silently approved."
            ),
            machine_reasons=[
                ModerationReasonRead(
                    code="image_moderation_unavailable",
                    label="Automatic visual moderation could not complete successfully.",
                    severity="medium",
                    evidence=attachment.original_filename,
                )
            ],
            flags={
                "fallback": True,
                "image_reviewed": False,
                "source": "openai-error-fallback",
                "attachment_filename": attachment.original_filename,
            },
            escalation_required=True,
        )

    def _aggregate_attachment_decisions(
        self,
        attachment_decisions: list[tuple[ModerationAttachmentDescriptor, LLMModerationDecision]],
    ) -> LLMModerationDecision:
        if not attachment_decisions:
            raise ValueError("attachment_decisions must not be empty.")

        decisions = [decision for _, decision in attachment_decisions]
        if any(decision.outcome == "reject" for decision in decisions):
            outcome = "reject"
        elif any(decision.outcome == "needs_manual_review" for decision in decisions):
            outcome = "needs_manual_review"
        else:
            outcome = "approve"

        summary = {
            "reject": "Image moderation rejected one or more attachments.",
            "needs_manual_review": (
                "Image moderation recommends manual review for one or more "
                "attachments."
            ),
            "approve": "Image moderation approved the submitted attachments.",
        }[outcome]

        user_safe_explanation = {
            "reject": (
                "One or more attached photos cannot be accepted. Please use civic evidence that "
                "avoids explicit sexual content, graphic violence, and unrelated imagery."
            ),
            "needs_manual_review": (
                "One or more attached photos need a quick human review before the report can "
                "move forward."
            ),
            "approve": "The attached photos look suitable to continue with the report.",
        }[outcome]

        internal_notes = " | ".join(
            f"{attachment.original_filename}: {decision.summary}"
            for attachment, decision in attachment_decisions
        )

        aggregated_reasons = self._deduplicate_reasons(
            [reason for _, decision in attachment_decisions for reason in decision.machine_reasons]
        )
        attachment_flags = [
            {
                "filename": attachment.original_filename,
                "content_type": attachment.content_type,
                "outcome": decision.outcome,
                "confidence": decision.confidence,
                "image_reviewed": bool(decision.flags.get("image_reviewed")),
                "matches_issue": decision.flags.get("matches_issue"),
                "relevance_score": decision.flags.get("relevance_score"),
                "source": decision.flags.get("source"),
            }
            for attachment, decision in attachment_decisions
        ]

        return self._build_decision(
            outcome=outcome,
            confidence=max(decision.confidence for decision in decisions),
            summary=summary,
            user_safe_explanation=user_safe_explanation,
            internal_notes=internal_notes,
            machine_reasons=aggregated_reasons,
            flags={
                "image_reviewed": any(
                    bool(decision.flags.get("image_reviewed")) for decision in decisions
                ),
                "fallback": any(bool(decision.flags.get("fallback")) for decision in decisions),
                "attachment_count": len(attachment_decisions),
                "attachment_reviews": attachment_flags,
            },
            escalation_required=outcome == "needs_manual_review",
        )

    @staticmethod
    def _build_decision(
        *,
        outcome: str,
        confidence: float,
        summary: str,
        user_safe_explanation: str,
        internal_notes: str,
        machine_reasons: list[ModerationReasonRead],
        flags: dict[str, object],
        escalation_required: bool = False,
    ) -> LLMModerationDecision:
        return LLMModerationDecision(
            outcome=outcome,
            confidence=confidence,
            summary=summary,
            user_safe_explanation=user_safe_explanation,
            internal_notes=internal_notes,
            machine_reasons=machine_reasons,
            normalized_category_slug=None,
            escalation_required=escalation_required,
            flags=flags,
        )

    def _looks_like_refusal(self, value: str) -> bool:
        lowered = value.lower()
        return any(marker in lowered for marker in self.config.refusal_markers)

    @staticmethod
    def _deduplicate_reasons(
        reasons: list[ModerationReasonRead],
    ) -> list[ModerationReasonRead]:
        seen: set[tuple[str, str | None]] = set()
        deduplicated: list[ModerationReasonRead] = []
        for reason in reasons:
            key = (reason.code, reason.evidence)
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(reason)
        return deduplicated
