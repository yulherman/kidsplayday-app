# ARCHITECTURE.md — Kids Activities Backend

System design notes. Pair with [AGENTS.md](./AGENTS.md) for conventions and [README.md](./README.md) for setup.

## High-level shape

```
┌──────────┐   HTTPS / JSON    ┌────────────────────────────────┐
│  Mobile  │ ────────────────▶ │  FastAPI (uvicorn workers)     │
│  client  │                   │  ├─ Routers (app/api/*)        │
└──────────┘                   │  ├─ Auth dep (JWT Bearer)      │
                               │  ├─ Service layer (ai_engine,  │
                               │  │   weather, verification)    │
                               │  └─ SQLAlchemy async session   │
                               └────┬──────────────┬────────────┘
                                    │              │
                                ┌───▼────┐    ┌────▼────┐
                                │ Postgres│    │  Redis  │
                                │   16   │    │    7    │
                                └────────┘    └─────────┘
                                    ▲
                                    │
                              ┌─────┴──────┐
                              │  OpenAI    │
                              │ OpenWeather│
                              └────────────┘
```

## Request lifecycle

1. Client sends `Authorization: Bearer <jwt>` to a route under `app/api/`.
2. `get_current_user` decodes the JWT (HS256), loads the `User` row, raises 401 on failure.
3. Router pulls a `AsyncSession` via `Depends(get_db)` — sessions auto-commit on success and rollback on exception.
4. Router calls into `app/services/` for any non-trivial logic (AI generation, weather, verification).
5. Response is serialized through a Pydantic v2 schema in `app/schemas/`.

## AI generation pipeline

Centerpiece: [app/services/ai_engine.py](app/services/ai_engine.py). For each `/activities/generate-plan` request:

1. **Resolve language** — `_resolve_language(language)` collapses everything to `en` or `uk`.
2. **Build system instruction** — `_build_system_instruction(lang)` concatenates `GENERATE_INSTRUCTIONS` + per-language encouragement examples.
3. **Build user prompt** — `_build_generation_prompt(...)` ([ai_engine.py:179](app/services/ai_engine.py#L179)) assembles:
   - Age profiles for each unique category present (`AGE_PROFILES` dict).
   - Multi-child joint-play rules + age-gap heuristics (small / moderate / large).
   - Weather context (force-indoor if not outdoor-OK).
   - Mode hint (`daily` / `evening` / `weekend` / `vacation`).
   - Location hint (`home` / `cafe` / `outdoor` / custom).
   - Materials, theme, energy level, favorites, exclusions.
4. **Call OpenAI** — `chat.completions.create` with `response_format=ACTIVITY_RESPONSE_SCHEMA` (strict JSON schema, see [ai_engine.py:40](app/services/ai_engine.py#L40)).
5. **Retry** on `RateLimitError` with exponential backoff (up to 5 retries) and on `APITimeoutError` (up to 2 retries). All other OpenAI errors surface as `ActivityGenerationError`.
6. **Normalize** — `_normalize_activity_keys` ([ai_engine.py:334](app/services/ai_engine.py#L334)) maps short LLM keys (`title`, `dur`, `cat`, ...) to full DB column names and duplicates the single-language text into both `_uk` and `_en` slots (the cross-language copy is later overwritten by translation).
7. **Safety filter** — `validate_activity` rejects unsafe content per child age. Rejected items are logged and dropped.
8. **Persist** — router writes accepted activities + a `UserActivityHistory` row.

### Multi-key OpenAI rotation

`settings.openai_api_keys` accepts a comma-separated list. `_get_openai_client()` ([ai_engine.py:100-107](app/services/ai_engine.py#L100-L107)) builds one `AsyncOpenAI` client per key and round-robins via `itertools.cycle`. Falls back to single `openai_api_key` if no list is set. A semaphore (`_ai_semaphore`, size 10) caps concurrent OpenAI calls per worker process.

### Translation

`translate_activities(activities, source, target)` reuses the OpenAI client and `TRANSLATE_INSTRUCTIONS` to fill the missing-language fields after generation when source ≠ target.

### Verification

`app/services/verification.py` re-asks the model whether an activity is safe / age-appropriate; results are stored in `ActivityVerification`.

## Data model (ER summary)

```
User ─┬─< Child ──────< UserActivityHistory >── Activity ─── ActivityVerification (1:1)
      │
      └─< HomeMaterial

ThemedWeek (standalone, seeded at startup via lifespan)
```

- `User`: email (unique), bcrypt `password_hash`, language, lat/lng, timezone, `is_premium`.
- `Child`: belongs to `User`, has `birth_date`. `age_months` / `age_category` are Python properties (see [models/user.py:38-56](app/models/user.py#L38-L56)).
- `HomeMaterial`: belongs to `User`, has name + category (crafts / sports / kitchen / outdoor) + availability flag.
- `Activity`: bilingual text fields, age range in months, duration, energy, category, weather suitability, JSONB lists for `materials_needed` and `developmental_goals`, aggregate counters.
- `UserActivityHistory`: status (`suggested` / `completed` / `skipped` / `liked` / `disliked` / `try_later`), rating 1–5, notes.
- `ActivityVerification`: score, source (`ai` / `community`), sample size, timestamp.
- `ThemedWeek`: seeded daily-plans JSONB + shopping-list JSONB.

## Auth

- Algorithm: HS256, configurable via `settings.algorithm`.
- TTL: 7 days (`settings.access_token_expire_minutes = 60 * 24 * 7`).
- Password hashing: bcrypt via `passlib`.
- Token issued at `/auth/register` and `/auth/login`; validated by `HTTPBearer` + `get_current_user`.

## Connection pool

`create_async_engine` ([db/database.py](app/db/database.py)): `pool_size=20`, `max_overflow=40`, `pool_pre_ping=True`, `pool_recycle=3600`. Tune in [app/db/database.py](app/db/database.py) if traffic scales.

## Deployment

- **Dockerfile** → installs `requirements.txt`, copies `app/` + `alembic/`, runs `start.sh`.
- **start.sh** → `alembic upgrade head` then `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers $WORKERS`.
- **Railway**: builder = Dockerfile, healthcheck = `GET /health`, restart on failure (up to 10 retries).

## External services

| Service | Purpose | Env |
| --- | --- | --- |
| OpenAI | Activity generation, translation, verification | `OPENAI_API_KEY` or `OPENAI_API_KEYS` |
| OpenWeather | Current weather by user coords for indoor/outdoor guidance | `OPENWEATHER_API_KEY` |
| Redis | Cache + rate-limiting primitives | `REDIS_URL` |

## Startup tasks

`lifespan` in [app/main.py](app/main.py) seeds `ThemedWeek` rows via `seed_themed_weeks` on each boot (idempotent).
