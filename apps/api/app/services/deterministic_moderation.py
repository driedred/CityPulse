from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from app.schemas.issue import DeterministicModerationDecision, ModerationReasonRead
from app.services.intelligence_utils import normalize_text
from app.services.moderation_models import ModerationSubmission

REPEATED_PUNCTUATION_PATTERN = re.compile(r"([!?.,])\1{2,}")
WORD_PATTERN = re.compile(r"[a-zA-Z']+")


@dataclass(frozen=True)
class DeterministicModerationThresholds:
    minimum_meaningful_tokens: int = 6
    minimum_description_length: int = 24
    excessive_caps_ratio: float = 0.45
    repeated_punctuation_triggers: int = 2
    repetition_ratio: float = 0.34
    title_repetition_limit: int = 2


@dataclass(frozen=True)
class DeterministicModerationConfig:
    profanity_terms: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "damn",
                "hell",
                "shit",
                "crap",
            }
        )
    )
    abusive_terms: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "idiot",
                "moron",
                "stupid",
                "lazy",
                "useless",
                "corrupt",
            }
        )
    )
    hate_placeholder_patterns: tuple[str, ...] = (
        r"\bgo back to\b",
        r"\bdon't belong here\b",
        r"\bthose people\b",
        r"\bthese people ruin\b",
    )
    spam_markers: tuple[str, ...] = (
        "buy now",
        "call me",
        "click here",
        "subscribe",
        "free money",
    )
    thresholds: DeterministicModerationThresholds = field(
        default_factory=DeterministicModerationThresholds
    )


class DeterministicModerationService:
    def __init__(
        self,
        *,
        config: DeterministicModerationConfig | None = None,
    ) -> None:
        self.config = config or DeterministicModerationConfig()
        self._hate_patterns = tuple(
            re.compile(pattern, flags=re.IGNORECASE)
            for pattern in self.config.hate_placeholder_patterns
        )

    def evaluate(self, submission: ModerationSubmission) -> DeterministicModerationDecision:
        title = normalize_text(submission.title, max_length=160)
        description = normalize_text(submission.short_description, max_length=4000)
        combined = f"{title} {description}".strip()
        lowered = combined.lower()
        alpha_characters = [char for char in combined if char.isalpha()]
        uppercase_letters = [char for char in alpha_characters if char.isupper()]
        tokens = list(WORD_PATTERN.findall(lowered))
        token_counts = Counter(tokens)
        unique_tokens = len(token_counts)
        profanity_hits = sorted({token for token in tokens if token in self.config.profanity_terms})
        abuse_hits = sorted({token for token in tokens if token in self.config.abusive_terms})
        hate_hits = [
            pattern.pattern
            for pattern in self._hate_patterns
            if pattern.search(combined)
        ]
        spam_hits = [marker for marker in self.config.spam_markers if marker in lowered]
        repeated_punctuation_hits = REPEATED_PUNCTUATION_PATTERN.findall(combined)
        title_occurrences_in_description = description.lower().count(title.lower()) if title else 0
        repetition_ratio = 0.0
        if tokens:
            repetition_ratio = 1 - (unique_tokens / len(tokens))

        reasons: list[ModerationReasonRead] = []
        flags: dict[str, object] = {
            "profanity_hits": profanity_hits,
            "abuse_hits": abuse_hits,
            "hate_hits": hate_hits,
            "spam_hits": spam_hits,
            "caps_ratio": round(
                len(uppercase_letters) / max(len(alpha_characters), 1),
                3,
            ),
            "repeated_punctuation_count": len(repeated_punctuation_hits),
            "meaningful_token_count": unique_tokens,
            "repetition_ratio": round(repetition_ratio, 3),
            "title_occurrences_in_description": title_occurrences_in_description,
            "attachment_count": len(submission.attachments),
        }

        if not self._coordinates_valid(submission.latitude, submission.longitude):
            reasons.append(
                ModerationReasonRead(
                    code="coordinate_invalid",
                    label="Coordinates are malformed or out of range.",
                    severity="high",
                    evidence=f"{submission.latitude}, {submission.longitude}",
                )
            )

        if unique_tokens < self.config.thresholds.minimum_meaningful_tokens or len(
            description
        ) < self.config.thresholds.minimum_description_length:
            reasons.append(
                ModerationReasonRead(
                    code="low_signal_description",
                    label="The report needs more concrete detail.",
                    severity="medium",
                    evidence=description[:120],
                )
            )

        if profanity_hits:
            reasons.append(
                ModerationReasonRead(
                    code="profanity_language",
                    label="The report contains profanity or obscene language.",
                    severity="medium",
                    evidence=", ".join(profanity_hits),
                )
            )

        if abuse_hits:
            severity = "high" if {"idiot", "moron", "useless"} & set(abuse_hits) else "medium"
            reasons.append(
                ModerationReasonRead(
                    code="direct_abuse",
                    label="The report uses insulting or demeaning language.",
                    severity=severity,
                    evidence=", ".join(abuse_hits),
                )
            )

        if hate_hits:
            reasons.append(
                ModerationReasonRead(
                    code="hate_placeholder_pattern",
                    label="The report includes exclusionary or hateful framing.",
                    severity="high",
                    evidence=hate_hits[0],
                )
            )

        if spam_hits:
            reasons.append(
                ModerationReasonRead(
                    code="spam_marker",
                    label="The report contains patterns commonly associated with spam.",
                    severity="high",
                    evidence=", ".join(spam_hits),
                )
            )

        if flags["caps_ratio"] >= self.config.thresholds.excessive_caps_ratio and len(
            alpha_characters
        ) >= 12:
            reasons.append(
                ModerationReasonRead(
                    code="excessive_caps",
                    label="The report uses excessive all-caps emphasis.",
                    severity="medium",
                    evidence=title[:80],
                )
            )

        if len(repeated_punctuation_hits) >= self.config.thresholds.repeated_punctuation_triggers:
            reasons.append(
                ModerationReasonRead(
                    code="rage_punctuation",
                    label="The report relies on repeated punctuation or rage emphasis.",
                    severity="medium",
                    evidence=combined[:120],
                )
            )

        if repetition_ratio >= self.config.thresholds.repetition_ratio:
            reasons.append(
                ModerationReasonRead(
                    code="suspicious_repetition",
                    label="The report repeats the same wording excessively.",
                    severity="medium",
                    evidence=combined[:160],
                )
            )

        if title_occurrences_in_description > self.config.thresholds.title_repetition_limit:
            reasons.append(
                ModerationReasonRead(
                    code="copy_paste_spam",
                    label="The report appears to repeat the same sentence without added detail.",
                    severity="high",
                    evidence=combined[:160],
                )
            )

        for attachment in submission.attachments:
            if not attachment.content_type or "/" not in attachment.content_type:
                reasons.append(
                    ModerationReasonRead(
                        code="invalid_attachment_metadata",
                        label="Attachment metadata is malformed.",
                        severity="high",
                        evidence=attachment.original_filename,
                    )
                )
                break

        reject_codes = {
            "coordinate_invalid",
            "hate_placeholder_pattern",
            "spam_marker",
            "copy_paste_spam",
        }
        if "direct_abuse" in {reason.code for reason in reasons} and "profanity_language" in {
            reason.code for reason in reasons
        }:
            reject_codes.add("direct_abuse")

        reject_reasons = [reason for reason in reasons if reason.code in reject_codes]
        if reject_reasons:
            return DeterministicModerationDecision(
                outcome="reject",
                confidence=0.92,
                summary="Deterministic moderation rejected the submission.",
                user_safe_explanation=self._user_explanation("reject", reject_reasons),
                internal_notes=self._internal_notes(reject_reasons, flags),
                machine_reasons=reasons,
                flags=flags,
                escalation_required=False,
            )

        if reasons:
            return DeterministicModerationDecision(
                outcome="needs_manual_review",
                confidence=0.71,
                summary="Deterministic moderation flagged the submission for human review.",
                user_safe_explanation=self._user_explanation("needs_manual_review", reasons),
                internal_notes=self._internal_notes(reasons, flags),
                machine_reasons=reasons,
                flags=flags,
                escalation_required=True,
            )

        return DeterministicModerationDecision(
            outcome="pass",
            confidence=0.88,
            summary="Deterministic moderation passed the submission.",
            user_safe_explanation=(
                "Your report is clear enough to continue through moderation."
            ),
            internal_notes="No deterministic moderation flags were triggered.",
            machine_reasons=[],
            flags=flags,
            escalation_required=False,
        )

    @staticmethod
    def _coordinates_valid(latitude: float, longitude: float) -> bool:
        return (
            math.isfinite(latitude)
            and math.isfinite(longitude)
            and -90 <= latitude <= 90
            and -180 <= longitude <= 180
        )

    @staticmethod
    def _internal_notes(
        reasons: list[ModerationReasonRead],
        flags: dict[str, object],
    ) -> str:
        reason_codes = ", ".join(reason.code for reason in reasons)
        return (
            f"Triggered reasons: {reason_codes or 'none'}. "
            f"Signal summary: {flags}."
        )

    @staticmethod
    def _user_explanation(
        outcome: str,
        reasons: list[ModerationReasonRead],
    ) -> str:
        codes = {reason.code for reason in reasons}
        if "hate_placeholder_pattern" in codes or "direct_abuse" in codes:
            return (
                "Please remove insulting or demeaning language and focus on the civic issue itself."
            )
        if "coordinate_invalid" in codes or "invalid_attachment_metadata" in codes:
            return "Please check the location and attachment information before resubmitting."
        if outcome == "reject":
            return (
                "This report cannot be accepted in its current form. Please restate it with "
                "specific facts and neutral language."
            )
        return (
            "Your report may need a quick review before it can move forward. Adding specific, "
            "factual details will help."
        )
