from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.issue import (
    DeterministicModerationDecision,
    LLMModerationDecision,
    ModerationReasonRead,
)
from app.services.image_moderation import ImageModerationService
from app.services.intelligence_utils import normalize_text, tokenize
from app.services.moderation_models import ModerationSubmission
from app.services.openai_client import AIServiceError, OpenAIResponsesClient
from app.services.prompt_templates import (
    build_llm_moderation_system_prompt,
    build_llm_moderation_user_prompt,
)


@dataclass(frozen=True)
class LLMModerationConfig:
    category_keyword_map: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "roads": ("road", "street", "crossing", "pothole", "sidewalk", "intersection"),
            "sanitation": ("trash", "garbage", "waste", "bin", "dumping", "litter"),
            "lighting": ("light", "lamp", "dark", "streetlight", "lighting"),
            "safety": ("unsafe", "crime", "dangerous", "harassment", "violent", "speeding"),
            "transport": ("bus", "train", "stop", "shelter", "transit", "station"),
        }
    )


class LLMModerationService:
    def __init__(
        self,
        *,
        client: OpenAIResponsesClient | None = None,
        config: LLMModerationConfig | None = None,
        image_service: ImageModerationService | None = None,
    ) -> None:
        self.client = client or OpenAIResponsesClient()
        self.config = config or LLMModerationConfig()
        self.image_service = image_service or ImageModerationService(client=self.client)

    async def review(
        self,
        submission: ModerationSubmission,
        deterministic_decision: DeterministicModerationDecision,
        *,
        allowed_category_slugs: set[str],
    ) -> LLMModerationDecision:
        image_decision = await self.image_service.review(submission)
        if image_decision is not None and image_decision.outcome == "reject":
            return self._combine_decisions(
                text_decision=None,
                image_decision=image_decision,
            )

        try:
            text_decision = await self.client.generate_structured_output(
                schema_name="citypulse_llm_moderation",
                schema_model=LLMModerationDecision,
                system_prompt=build_llm_moderation_system_prompt(),
                user_prompt=build_llm_moderation_user_prompt(submission),
            )
            text_decision = self._normalize_category(
                text_decision,
                allowed_category_slugs=allowed_category_slugs,
            )
        except AIServiceError:
            text_decision = self._fallback_decision(
                submission,
                deterministic_decision,
                allowed_category_slugs=allowed_category_slugs,
            )

        return self._combine_decisions(
            text_decision=text_decision,
            image_decision=image_decision,
        )

    def _fallback_decision(
        self,
        submission: ModerationSubmission,
        deterministic_decision: DeterministicModerationDecision,
        *,
        allowed_category_slugs: set[str],
    ) -> LLMModerationDecision:
        combined = normalize_text(
            f"{submission.title} {submission.short_description}",
            max_length=4160,
        ).lower()
        tokens = tokenize(combined)
        reason_codes = {reason.code for reason in deterministic_decision.machine_reasons}
        reasons: list[ModerationReasonRead] = []

        if any(marker in combined for marker in ("http://", "https://", "buy now", "call me")):
            reasons.append(
                ModerationReasonRead(
                    code="off_topic_or_commercial",
                    label="The report appears promotional or unrelated to a civic issue.",
                    severity="high",
                    evidence=combined[:140],
                )
            )

        if any(
            phrase in combined
            for phrase in ("they don't care", "everyone knows", "obviously corrupt")
        ):
            reasons.append(
                ModerationReasonRead(
                    code="manipulative_framing",
                    label="The report relies on unsupported accusation or manipulative framing.",
                    severity="medium",
                    evidence=combined[:140],
                )
            )

        if len(tokens) < 8 or "low_signal_description" in reason_codes:
            reasons.append(
                ModerationReasonRead(
                    code="low_actionability",
                    label="The report may need more specific facts to be actionable.",
                    severity="medium",
                    evidence=submission.short_description[:140],
                )
            )

        if "direct_abuse" in reason_codes or "hate_placeholder_pattern" in reason_codes:
            reasons.append(
                ModerationReasonRead(
                    code="abusive_framing",
                    label="The submission still contains language that can derail review.",
                    severity="high",
                    evidence=submission.title[:120],
                )
            )

        if any(reason.code == "off_topic_or_commercial" for reason in reasons):
            return LLMModerationDecision(
                outcome="reject",
                confidence=0.84,
                summary="Contextual moderation rejected the report as off-topic or promotional.",
                user_safe_explanation=(
                    "This submission does not read like a civic issue report. Please describe "
                    "the local issue, its location, and observable facts."
                ),
                internal_notes=(
                    "Fallback contextual moderation identified commercial or off-topic markers."
                ),
                machine_reasons=reasons,
                normalized_category_slug=self._suggest_category(submission, allowed_category_slugs),
                escalation_required=False,
                flags={"fallback": True, "reason_codes": sorted(reason_codes)},
            )

        if reasons or deterministic_decision.outcome == "needs_manual_review":
            return LLMModerationDecision(
                outcome="needs_manual_review",
                confidence=0.69,
                summary="Contextual moderation recommends manual review.",
                user_safe_explanation=(
                    "Your report can be reviewed, but it may need a quick human check before "
                    "it moves forward."
                ),
                internal_notes=(
                    "Fallback contextual moderation escalated the issue because the content was "
                    "ambiguous, emotionally charged, or too low-signal for automatic approval."
                ),
                machine_reasons=reasons
                or [
                    ModerationReasonRead(
                        code="fallback_manual_review",
                        label="Automated contextual moderation was unavailable.",
                        severity="medium",
                    )
                ],
                normalized_category_slug=self._suggest_category(submission, allowed_category_slugs),
                escalation_required=True,
                flags={"fallback": True, "reason_codes": sorted(reason_codes)},
            )

        return LLMModerationDecision(
            outcome="approve",
            confidence=0.78,
            summary="Contextual moderation approved the report.",
            user_safe_explanation=(
                "Your report is specific enough to continue through the civic workflow."
            ),
            internal_notes=(
                "Fallback contextual moderation approved the issue without additional flags."
            ),
            machine_reasons=[],
            normalized_category_slug=self._suggest_category(submission, allowed_category_slugs),
            escalation_required=False,
            flags={"fallback": True, "reason_codes": sorted(reason_codes)},
        )

    @staticmethod
    def _normalize_category(
        decision: LLMModerationDecision,
        *,
        allowed_category_slugs: set[str],
    ) -> LLMModerationDecision:
        if (
            decision.normalized_category_slug
            and decision.normalized_category_slug not in allowed_category_slugs
        ):
            return decision.model_copy(update={"normalized_category_slug": None})
        return decision

    def _combine_decisions(
        self,
        *,
        text_decision: LLMModerationDecision | None,
        image_decision: LLMModerationDecision | None,
    ) -> LLMModerationDecision:
        if text_decision is None and image_decision is None:
            raise ValueError("At least one moderation decision is required.")
        if text_decision is None:
            return image_decision  # type: ignore[return-value]
        if image_decision is None:
            return text_decision

        if "reject" in {text_decision.outcome, image_decision.outcome}:
            outcome = "reject"
        elif "needs_manual_review" in {
            text_decision.outcome,
            image_decision.outcome,
        }:
            outcome = "needs_manual_review"
        else:
            outcome = "approve"

        return LLMModerationDecision(
            outcome=outcome,
            confidence=max(text_decision.confidence, image_decision.confidence),
            summary=self._compose_summary(
                outcome=outcome,
                text_decision=text_decision,
                image_decision=image_decision,
            ),
            user_safe_explanation=self._compose_user_safe_explanation(
                outcome=outcome,
                text_decision=text_decision,
                image_decision=image_decision,
            ),
            internal_notes=(
                f"Text moderation: {text_decision.internal_notes} "
                f"Image moderation: {image_decision.internal_notes}"
            ),
            machine_reasons=self._deduplicate_reasons(
                [
                    *text_decision.machine_reasons,
                    *image_decision.machine_reasons,
                ]
            ),
            normalized_category_slug=text_decision.normalized_category_slug,
            escalation_required=(
                outcome == "needs_manual_review"
                or text_decision.escalation_required
                or image_decision.escalation_required
            ),
            flags={
                **text_decision.flags,
                "image_reviewed": bool(image_decision.flags.get("image_reviewed")),
                "image_moderation_checked": True,
                "fallback": bool(text_decision.flags.get("fallback"))
                or bool(image_decision.flags.get("fallback")),
                "text_moderation": text_decision.flags,
                "image_moderation": image_decision.flags,
            },
        )

    @staticmethod
    def _compose_summary(
        *,
        outcome: str,
        text_decision: LLMModerationDecision,
        image_decision: LLMModerationDecision,
    ) -> str:
        if outcome == "reject":
            if image_decision.outcome == "reject":
                return (
                    "Contextual moderation rejected the report because an "
                    "attachment was not acceptable."
                )
            return "Contextual moderation rejected the report."
        if outcome == "needs_manual_review":
            if image_decision.outcome == "needs_manual_review":
                return (
                    "Contextual moderation recommends manual review because an "
                    "attachment needs verification."
                )
            return "Contextual moderation recommends manual review."
        return text_decision.summary

    @staticmethod
    def _compose_user_safe_explanation(
        *,
        outcome: str,
        text_decision: LLMModerationDecision,
        image_decision: LLMModerationDecision,
    ) -> str:
        if outcome == "reject":
            return (
                image_decision.user_safe_explanation
                if image_decision.outcome == "reject"
                else text_decision.user_safe_explanation
            )
        if outcome == "needs_manual_review" and image_decision.outcome == "needs_manual_review":
            return image_decision.user_safe_explanation
        return text_decision.user_safe_explanation

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

    def _suggest_category(
        self,
        submission: ModerationSubmission,
        allowed_category_slugs: set[str],
    ) -> str | None:
        lowered = normalize_text(
            f"{submission.title} {submission.short_description}",
            max_length=4160,
        ).lower()
        best_slug = submission.category_slug
        best_score = 0
        for slug, keywords in self.config.category_keyword_map.items():
            if slug not in allowed_category_slugs:
                continue
            score = sum(lowered.count(keyword) for keyword in keywords)
            if score > best_score:
                best_slug = slug
                best_score = score
        return best_slug if best_slug in allowed_category_slugs else None
