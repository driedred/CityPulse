# CityPulse Moderation Pipeline

## Overview

CityPulse uses a two-layer moderation pipeline so reports can be filtered for abuse, manipulation, and low-signal content without turning the product into a hostile gatekeeper.

The pipeline is intentionally split into:

1. Deterministic moderation
2. Contextual LLM moderation
3. Assistive AI rewrite

Every moderation layer writes an audit row into `moderation_results`. The issue record stores the synthesized status that the product uses for citizen and admin workflows.

## Layer 1: Deterministic Moderation

`DeterministicModerationService` runs first.

Current checks include:

- Profanity and obscene language
- Direct insults and abusive framing
- Placeholder hate/exclusionary patterns
- Excessive all-caps emphasis
- Rage punctuation and spammy emphasis
- Content that is too short or low-signal
- Suspicious repetition and copy-paste style spam
- Invalid coordinates and malformed attachment metadata

Possible deterministic outcomes:

- `pass`
- `reject`
- `needs_manual_review`

Each deterministic decision returns:

- machine reasons
- user-safe explanation
- internal notes
- confidence
- structured flags with heuristic metrics

## Layer 2: Contextual LLM Moderation

`LLMModerationService` runs after deterministic moderation unless the deterministic layer hard-rejects the report.

The contextual layer reviews:

- Title
- Description
- Category
- Locale
- Coordinates
- Attachment descriptors

Possible contextual outcomes:

- `approve`
- `reject`
- `needs_manual_review`

The LLM response is validated against a Pydantic schema before the result is accepted.

Stored fields include:

- concise summary
- user-safe explanation
- internal notes
- machine reasons
- optional normalized category slug
- escalation flag
- provider/model metadata

## OpenAI Integration

The live contextual layer uses the OpenAI Responses API surface through `OpenAIResponsesClient`.

Key implementation details:

- Configured model defaults to `gpt-5.4-mini`
- Prompts are isolated in `prompt_templates.py`
- Structured JSON is requested with a JSON Schema payload
- Response payloads are validated with Pydantic
- Retry and timeout handling are built into the client

If OpenAI is unavailable or not configured:

- contextual moderation falls back to local heuristic review logic
- rewrite falls back to a deterministic cleanup pass

This keeps local development and tests functional without disabling the overall moderation architecture.

## Issue State Mapping

Moderation outcomes are converted into issue states as follows:

- deterministic or contextual `reject` -> `issue.status = rejected`
- contextual `needs_manual_review` -> `issue.status = pending_moderation`, `moderation_state = under_review`
- contextual `approve` -> `issue.status = approved`, `moderation_state = completed`

`published` remains a separate operational visibility state.

## Assistive AI Rewrite

`AIRewriteService` is not a moderation replacement. It helps citizens restate a report in a more constructive and actionable form.

Rewrite output includes:

- rewritten title
- rewritten description
- short explanation of improvements
- tone classification

The user keeps the original draft until they explicitly accept the rewrite.

## Admin Auditability

Admins can inspect moderation through:

- recent moderation issue list
- issue-level audit detail
- rerun moderation endpoint

The admin surface includes:

- deterministic flags
- contextual moderation summary
- safe user explanation
- internal notes
- escalation flags

The system intentionally avoids storing or exposing chain-of-thought style reasoning.
