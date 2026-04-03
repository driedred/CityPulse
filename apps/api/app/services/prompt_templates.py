from __future__ import annotations

from app.services.moderation_models import ModerationSubmission


def build_llm_moderation_system_prompt() -> str:
    return (
        "You are a civic issue moderation assistant for a government technology platform. "
        "Review issue reports for relevance, abuse, manipulation, low-signal writing, "
        "bad-faith framing, and civic actionability. Return concise structured JSON only. "
        "Do not include chain-of-thought. Keep user-facing explanations calm, specific, and short."
    )


def build_llm_moderation_user_prompt(submission: ModerationSubmission) -> str:
    attachment_lines = "\n".join(
        [
            f"- filename: {attachment.original_filename}; "
            f"content_type: {attachment.content_type}; "
            f"size_bytes: {attachment.size_bytes}"
            for attachment in submission.attachments
        ]
    )
    return (
        "Review the following civic issue submission.\n\n"
        f"Issue ID: {submission.issue_id}\n"
        f"Category slug: {submission.category_slug}\n"
        f"Source locale: {submission.source_locale}\n"
        f"Latitude: {submission.latitude}\n"
        f"Longitude: {submission.longitude}\n"
        f"Title: {submission.title}\n"
        f"Description: {submission.short_description}\n"
        "Attachment descriptors:\n"
        f"{attachment_lines or '- none'}\n\n"
        "Evaluate whether the submission should be approved, rejected, or sent to manual review. "
        "Reject only for clearly abusive, manipulative, hateful, irrelevant, or bad-faith content. "
        "Use manual review when context is ambiguous or when the submission needs human judgment. "
        "If the text implies a better category, suggest the normalized category slug."
    )


def build_ai_rewrite_system_prompt() -> str:
    return (
        "You are a civic writing assistant. Rewrite issue reports to stay factual, calm, "
        "and actionable while preserving the author's meaning. Remove insults, accusations, "
        "and manipulative framing without turning the text into stiff bureaucracy. "
        "Return concise structured JSON only."
    )


def build_ai_rewrite_user_prompt(
    *,
    title: str,
    short_description: str,
    category_slug: str | None,
    source_locale: str,
    context_hint: str | None,
) -> str:
    return (
        "Rewrite this civic issue report more constructively.\n\n"
        f"Category slug: {category_slug or 'unknown'}\n"
        f"Source locale: {source_locale}\n"
        f"Context hint: {context_hint or 'none'}\n"
        f"Original title: {title}\n"
        f"Original description: {short_description}\n\n"
        "Keep the core complaint and observed facts. Improve specificity, tone, and actionability."
    )
