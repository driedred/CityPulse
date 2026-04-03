# CityPulse API

Backend service for CityPulse built with FastAPI, SQLAlchemy, Alembic, and JWT authentication.

## Local setup

1. Create and activate a Python 3.12+ virtual environment.
2. Copy `.env.example` to `.env`.
3. Install with `pip install -e .[dev]`.
4. Run `alembic -c alembic.ini upgrade head`.
5. Run `python -m app.scripts.seed`.
6. Start the API with `uvicorn app.main:app --reload`.

## AI placeholder config

- `OPENAI_MODEL` defaults to `gpt-5.4-mini` for future rewrite and moderation integrations.
- Set `OPENAI_API_KEY` to enable live OpenAI-backed contextual moderation and rewrite calls.
- `OPENAI_API_BASE_URL`, `OPENAI_TIMEOUT_SECONDS`, and `OPENAI_MAX_RETRIES` control network behavior for the OpenAI client.

## Integrity layer

- User trust and abuse snapshots are stored in `user_integrity_snapshots`.
- Operational abuse events are logged in `integrity_events`.
- Trust weighting is bounded and feeds impact scoring internally.
- Default thresholds and formulas are documented in `../../docs/trust-and-abuse.md`.

## Implemented endpoints

- `GET /api/admin/moderation/issues`
- `GET /api/admin/moderation/issues/{issue_id}`
- `POST /api/admin/moderation/issues/{issue_id}/rerun`
- `GET /api/admin/users`
- `GET /api/admin/users/{user_id}/integrity`
- `POST /api/admin/users/{user_id}/integrity/recalculate`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/users/me`
- `POST /api/issues`
- `POST /api/issues/{issue_id}/attachments`
- `GET /api/issues/me`
- `GET /api/issues/{issue_id}/impact`
- `GET /api/issues/{issue_id}/impact/admin`
- `POST /api/issues/{issue_id}/impact/recalculate`
- `GET /api/public/categories`
- `GET /api/public/issues`
- `GET /api/public/issues/feed`
- `GET /api/public/issues/map`
- `GET /api/public/issues/{issue_id}`
- `GET /api/public/issues/{issue_id}/impact`
- `POST /api/public/issues/{issue_id}/feedback`
- `POST /api/public/issues/{issue_id}/support`
- `POST /api/public/issues/duplicates`
- `POST /api/public/issues/rewrite`
- `POST /api/tickets`
- `GET /api/tickets/me`
- `GET /api/health`
