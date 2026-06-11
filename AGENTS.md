# AGENTS.md — Kids Activities Backend

This file is the primary context document for AI coding agents (Claude Code, Cursor, etc.) working in this repository. Read this before making changes.

## Project overview

AI-powered daily activity planner backend for kids aged 0–12. Generates age-appropriate, weather-aware, bilingual (English / Ukrainian) activity plans via OpenAI, persists user data and activity history in Postgres, and serves them through a FastAPI HTTP API consumed by an Expo React Native client.

## Stack

- Python 3.12 + FastAPI 0.115
- SQLAlchemy 2.0 async + asyncpg + PostgreSQL 16
- Alembic migrations
- Redis 7
- OpenAI (`gpt-4.1` by default; multi-key round-robin supported)
- JWT (HS256, 7-day expiry) + bcrypt
- Docker Compose for local dev; Railway for deployment

## Repository layout

```
app/
├── main.py              FastAPI app, CORS, router wiring, lifespan seeder
├── config.py            pydantic-settings Settings loaded from .env
├── pages.py             Inline HTML for /privacy and /support
├── api/                 HTTP routers (one file per resource)
│   ├── auth.py             /auth/register, /auth/login, /auth/location, /auth/language, /auth/me
│   ├── children.py         /children CRUD (max 2 per account)
│   ├── materials.py        /materials catalog + user inventory
│   ├── activities.py       /activities/generate-plan, /emergency, /by-materials, history, rating
│   ├── themed_weeks.py     /themed-weeks
│   └── premium.py          Premium gating + limits
├── core/
│   ├── security.py         hash_password, verify_password, create/decode_access_token
│   └── dependencies.py     get_current_user (Bearer scheme)
├── db/
│   └── database.py         async_engine, async_session, get_db dependency
├── models/                 SQLAlchemy 2.0 Mapped[...] models
│   ├── base.py             DeclarativeBase
│   ├── user.py             User, Child, HomeMaterial (+ age_months/age_category props)
│   └── activity.py         Activity, UserActivityHistory, ActivityVerification, ThemedWeek
├── schemas/                Pydantic v2 request/response models (user.py, activity.py)
├── services/
│   ├── ai_engine.py        Prompt assembly + OpenAI call + JSON parsing + safety filter
│   ├── weather.py          OpenWeather lookup by lat/lng
│   ├── verification.py     AI self-verification of generated activities
│   ├── safety_validator.py Rule-based reject of unsafe content
│   ├── seed_themed_weeks.py Lifespan seed
│   └── notifications.py    Push notification helpers
└── prompts/                Static LLM instructions loaded at import time
    ├── __init__.py         _load() / _load_dir() helpers
    ├── generate_instructions.txt
    ├── translate_instructions.txt
    ├── verify_instructions.txt
    ├── ages/               baby.txt, explorer.txt, toddler.txt, preschool.txt, junior.txt, tween.txt
    ├── languages/          en.txt, uk.txt
    └── encouragement/      en.txt, uk.txt
alembic/                    Migration env + versions/
load_test/                  Locust scenarios
```

## Domain glossary

- **Age categories** (from [app/models/user.py:44-56](app/models/user.py#L44-L56)):
  | Category | Months | Approx. age |
  | --- | --- | --- |
  | `baby` | 0–11 | 0–1 yr |
  | `explorer` | 12–23 | 1–2 yr |
  | `toddler` | 24–47 | 2–4 yr |
  | `preschool` | 48–71 | 4–6 yr |
  | `junior` | 72–107 | 6–9 yr |
  | `tween` | 108+ | 9–12 yr |

- **Modes** (from [app/services/ai_engine.py:130-135](app/services/ai_engine.py#L130-L135)): `daily`, `evening`, `weekend`, `vacation`. Auto-selected via `determine_mode(age, is_vacation, day_of_week)`.
- **Locations**: `home`, `cafe`, `outdoor`, or a free-form custom string. See `LOCATION_HINTS` / `LOCATION_CUSTOM`.
- **Energy levels**: `calm`, `moderate`, `active`.
- **Categories**: `creative`, `science`, `sport`, `cooking`, `outdoor`, `social`, `sensory`, `music`, `logic`.
- **Languages**: `en`, `uk`. All activity text fields are stored bilingually (`*_uk` + `*_en`).

## Conventions

- **Async only.** All DB code uses `AsyncSession`. Inject via `db: AsyncSession = Depends(get_db)`.
- **Auth.** Protected routes use `user: User = Depends(get_current_user)`. Don't roll your own auth.
- **SQLAlchemy 2.0 style.** Use typed `Mapped[...]` and `mapped_column(...)`. Primary keys are `uuid.UUID` with `default=uuid.uuid4`.
- **Pydantic v2.** Schemas live in `app/schemas/`. Use `model_validate(...)`, not `.from_orm()`.
- **Bilingual content.** Any new user-facing text field on `Activity` must come in both `_uk` and `_en` variants. The AI engine normalizes both directions in `_normalize_activity_keys` ([ai_engine.py:334](app/services/ai_engine.py#L334)).
- **Prompts live in `app/prompts/`.** Never inline prompt strings in Python. Add a new `.txt` file and load it via `_load` / `_load_dir` in [app/prompts/__init__.py](app/prompts/__init__.py).
- **Structured OpenAI outputs.** Use the JSON schema in `ACTIVITY_RESPONSE_SCHEMA` ([ai_engine.py:40](app/services/ai_engine.py#L40)); never parse free-form text.
- **Rate limit retries** are already centralized in `generate_activities` — don't sprinkle retry logic into routers.
- **Errors.** Use `HTTPException` in routers; raise `ActivityGenerationError(user_message, internal_reason)` from the AI layer.
- **CORS origins** come from `ALLOWED_ORIGINS` env (comma-separated) — keep it that way.

## Commands cheatsheet

```bash
# Local stack
docker-compose up -d --build
docker-compose logs api --tail=120
docker-compose restart api
docker-compose down

# Migrations
docker-compose exec api alembic revision --autogenerate -m "describe change"
docker-compose exec api alembic upgrade head
docker-compose exec api alembic downgrade -1

# Quick smoke
curl -i http://localhost:8000/health
curl -i -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.test","password":"123456","language":"en"}'
```

## Don'ts

- Don't commit `.env`. `.env.example` is the only checked-in template.
- Don't add a new top-level dependency without pinning it in `requirements.txt`.
- Don't introduce sync SQLAlchemy code (sessions, queries, drivers) — everything is async.
- Don't hardcode prompt text in Python. Add a `.txt` file under `app/prompts/`.
- Don't bypass `safety_validator.validate_activity` when persisting AI-generated content.
- Don't add tests that mock the database — the project's convention is integration tests against a real Postgres. (There is currently no test suite; flag this and ask the user before adding one.)

## Where to read first

When picking up a new task:

1. [app/main.py](app/main.py) — see which routers are mounted.
2. [app/config.py](app/config.py) — see what env knobs exist.
3. The relevant router under [app/api/](app/api/) — that's where every feature starts.
4. [app/services/ai_engine.py](app/services/ai_engine.py) — for anything touching activity generation.
5. [ARCHITECTURE.md](./ARCHITECTURE.md) — for deeper system flow.

## Brand naming

In files under `docs/legal/` and `docs/app-store/` (frontend repo), replace "PlayDay" with "Kids Activities" before publishing. Repo names (`playday-backend`, `playday-app`) stay as-is internally.
