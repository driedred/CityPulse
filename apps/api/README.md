# CityPulse API

Backend service for CityPulse built with FastAPI, SQLAlchemy, Alembic, and JWT authentication.

## Local setup

1. Create and activate a Python 3.12+ virtual environment.
2. Copy `.env.example` to `.env`.
3. Install with `pip install -e .[dev]`.
4. Run `alembic -c alembic.ini upgrade head`.
5. Run `python -m app.scripts.seed`.
6. Start the API with `uvicorn app.main:app --reload`.

## Implemented endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/users/me`
- `POST /api/issues`
- `POST /api/issues/{issue_id}/attachments`
- `GET /api/issues/me`
- `POST /api/tickets`
- `GET /api/tickets/me`
- `GET /api/health`
