from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.issue import AIRewriteStructuredResponse, IssueRewriteRequest, IssueRewriteResponse
from app.services.intelligence_utils import normalize_text
from app.services.openai_client import AIServiceError, OpenAIResponsesClient
from app.services.prompt_templates import (
    build_ai_rewrite_system_prompt,
    build_ai_rewrite_user_prompt,
)


@dataclass(frozen=True)
class AIRewriteConfig:
    accusation_patterns: tuple[tuple[str, str], ...] = (
        (r"\b(lazy|useless|corrupt)\b", ""),
        (r"\bthis is (a )?disgusting mess\b", "This area needs cleanup"),
        (r"\bsomeone needs to fix this asap\b", "Please inspect and address this issue soon"),
        (r"\bwhat is wrong with (them|the city)\b", ""),
    )


class AIRewriteService:
    def __init__(
        self,
        *,
        client: OpenAIResponsesClient | None = None,
        config: AIRewriteConfig | None = None,
    ) -> None:
        self.client = client or OpenAIResponsesClient()
        self.config = config or AIRewriteConfig()

    async def rewrite(
        self,
        payload: IssueRewriteRequest,
        *,
        category_slug: str | None = None,
    ) -> IssueRewriteResponse:
        try:
            structured = await self.client.generate_structured_output(
                schema_name="citypulse_ai_rewrite",
                schema_model=AIRewriteStructuredResponse,
                system_prompt=build_ai_rewrite_system_prompt(),
                user_prompt=build_ai_rewrite_user_prompt(
                    title=payload.title,
                    short_description=payload.short_description,
                    category_slug=category_slug,
                    source_locale=payload.source_locale,
                    context_hint=payload.context_hint,
                ),
                max_output_tokens=700,
            )
            return IssueRewriteResponse(
                rewritten_title=structured.rewritten_title,
                rewritten_description=structured.rewritten_description,
                explanation=structured.explanation,
                tone_classification=structured.tone_classification,
            )
        except AIServiceError:
            return self._fallback_rewrite(payload)

    def _fallback_rewrite(self, payload: IssueRewriteRequest) -> IssueRewriteResponse:
        normalized_title = self._sentence_case(normalize_text(payload.title, max_length=160))
        normalized_description = normalize_text(
            payload.short_description,
            max_length=4000,
        )
        tone_classification = self._classify_tone(payload.title, payload.short_description)
        improvements: list[str] = []

        if normalized_title.isupper() or payload.title != normalized_title:
            improvements.append("reduced all-caps emphasis")

        rewritten_description = normalized_description
        for pattern, replacement in self.config.accusation_patterns:
            updated = re.sub(pattern, replacement, rewritten_description, flags=re.IGNORECASE)
            if updated != rewritten_description:
                improvements.append("removed accusatory language")
                rewritten_description = updated

        rewritten_description = re.sub(r"([!?.,])\1{1,}", r"\1", rewritten_description)
        rewritten_description = re.sub(r"\s+", " ", rewritten_description).strip(" .")
        if rewritten_description and not rewritten_description.endswith("."):
            rewritten_description = f"{rewritten_description}."

        if "please" not in rewritten_description.lower():
            rewritten_description = (
                f"{rewritten_description} Please review the location and address the issue."
            )
            improvements.append("made the request more actionable")

        explanation = "Improved clarity and tone while keeping the main issue intact."
        if improvements:
            explanation = (
                "Improved the draft by "
                + ", ".join(sorted(set(improvements)))
                + "."
            )

        return IssueRewriteResponse(
            rewritten_title=normalized_title,
            rewritten_description=rewritten_description,
            explanation=explanation,
            tone_classification=tone_classification,
        )

    @staticmethod
    def _sentence_case(value: str) -> str:
        if not value:
            return value
        lower = value.lower()
        return lower[:1].upper() + lower[1:]

    @staticmethod
    def _classify_tone(title: str, description: str) -> str:
        combined = f"{title} {description}"
        alpha_chars = [char for char in combined if char.isalpha()]
        uppercase_chars = [char for char in alpha_chars if char.isupper()]
        caps_ratio = len(uppercase_chars) / max(len(alpha_chars), 1)
        lowered = combined.lower()
        if caps_ratio > 0.45 or "!!!" in combined:
            return "rage"
        if any(word in lowered for word in ("corrupt", "lazy", "useless", "blame")):
            return "accusatory"
        if len(lowered.split()) < 10:
            return "low_signal"
        if any(word in lowered for word in ("angry", "upset", "frustrated", "disgusting")):
            return "frustrated"
        return "neutral"
