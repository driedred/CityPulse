# CityPulse

CityPulse is a production-oriented monorepo scaffold for a civic issue reporting platform. It is structured for a shared product surface with a public landing experience, a citizen workflow, and an admin workflow, while keeping the frontend and backend deployable as independent services.

## Stack

- Frontend: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui-style primitives, Framer Motion
- Backend: FastAPI, Python 3.12
- Database: PostgreSQL with PostGIS
- Cache and queue foundation: Redis
- Object storage abstraction: S3-compatible API
- Containers: Docker and Docker Compose

## Monorepo Structure

```text
.
|-- apps
|   |-- api
|   |   |-- app
|   |   |   |-- api
|   |   |   |-- core
|   |   |   |-- db
|   |   |   |-- middleware
|   |   |   |-- models
|   |   |   |-- schemas
|   |   |   |-- scripts
|   |   |   |-- services
|   |   |   `-- tasks
|   |   |-- alembic
|   |   |-- .env.example
|   |   |-- alembic.ini
|   |   |-- Dockerfile
|   |   |-- pyproject.toml
|   |   `-- tests
|   `-- web
|       |-- src
|       |   |-- app
|       |   |-- components
|       |   `-- lib
|       |-- .env.example
|       |-- components.json
|       |-- Dockerfile
|       `-- package.json
|-- docs
|   |-- architecture.md
|   `-- impact-score.md
|-- packages
|   `-- README.md
|-- docker-compose.yml
|-- package.json
`-- pnpm-workspace.yaml
```

## Local Run

### Option 1: Docker Compose

1. From the repository root, run `docker compose up --build`.
2. Open [http://localhost:3000](http://localhost:3000) for the frontend.
3. Hit [http://localhost:8000/api/health](http://localhost:8000/api/health) for the backend health endpoint.

### Option 2: Native Development

#### Frontend

1. Install `pnpm` and Node.js 20 or newer.
2. From the repository root, run `pnpm install`.
3. Copy `apps/web/.env.example` to `apps/web/.env.local`.
4. Run `pnpm --dir apps/web dev`.

#### Backend

1. Install Python 3.12.
2. Create a virtual environment inside `apps/api`.
3. Copy `apps/api/.env.example` to `apps/api/.env`.
4. Install the package from `apps/api` with `pip install -e .`.
5. Run `alembic -c alembic.ini upgrade head` from `apps/api`.
6. Run `python -m app.scripts.seed` from `apps/api`.
7. Run `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` from `apps/api`.

## Default Routes

- Public landing: `/en`
- Citizen workspace shell: `/en/dashboard`
- Admin workspace shell: `/en/admin`
- Backend health: `/api/health`

## Notes

- Locale-aware routing starts with `/[locale]` and defaults to `en`.
- The backend now includes JWT auth, role-aware models, Alembic migrations, seed data, and API tests.
- The backend AI integration surface now defaults `OPENAI_MODEL` to `gpt-5.4-mini`.
- The architecture overview lives in [docs/architecture.md](docs/architecture.md).
- Impact scoring and duplicate detection are documented in [docs/impact-score.md](docs/impact-score.md).
