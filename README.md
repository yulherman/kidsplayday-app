# Kids Activities — Backend

FastAPI бекенд для AI-генератора щоденних активностей для дітей 0–12 років. Генерує персоналізовані плани через OpenAI з урахуванням віку дитини, погоди, доступних матеріалів і часу.

## Стек

- **Python 3.12** + **FastAPI 0.115**
- **SQLAlchemy 2.0** (async) + **asyncpg** + **PostgreSQL 16**
- **Alembic** — міграції
- **Redis 7** — кеш / черги
- **OpenAI API** (`gpt-4.1`) — генерація та переклад активностей
- **JWT** (HS256, 7 днів) + **bcrypt** — автентифікація
- **Docker Compose** — локальний dev

## Швидкий старт

```bash
cp .env.example .env          # заповнити OPENAI_API_KEY, OPENWEATHER_API_KEY, SECRET_KEY
docker-compose up -d --build  # піднімає db + redis + api
docker-compose exec api alembic upgrade head
curl http://localhost:8000/health   # {"status":"ok","service":"playday-api"}
```

Swagger UI: http://localhost:8000/docs

## Корисні команди

```bash
# Логи / рестарт
docker-compose logs api --tail=120
docker-compose restart api

# Міграції
docker-compose exec api alembic revision --autogenerate -m "опис змін"
docker-compose exec api alembic upgrade head

# Перезбірка
docker-compose down
docker-compose up -d --build
```

## Структура

```
app/
├── main.py          # точка входу FastAPI, CORS, реєстрація роутерів
├── config.py        # pydantic Settings (env-змінні)
├── api/             # HTTP роутери: auth, children, materials, activities, themed_weeks, premium
├── core/            # security (JWT + bcrypt), dependencies (get_current_user)
├── db/              # async engine + сесія
├── models/          # SQLAlchemy 2.0 моделі (User, Child, Activity, ...)
├── schemas/         # Pydantic v2 схеми запитів/відповідей
├── services/        # ai_engine, weather, verification, safety_validator, ...
├── prompts/         # текстові інструкції для LLM (ages, languages, encouragement)
└── pages.py         # статичні /privacy і /support HTML
alembic/             # історія міграцій
load_test/           # Locust сценарії
```

## Деплой

Dockerfile + `start.sh` запускає `alembic upgrade head`, потім `uvicorn` з `WORKERS` env. Платформа: Railway, healthcheck — `GET /health`.

## Більше документації

- [ARCHITECTURE.md](./ARCHITECTURE.md) — деталі архітектури (AI pipeline, потоки даних, ER).
- [AGENTS.md](./AGENTS.md) — інструкції для AI-агентів (Claude Code, Cursor тощо).
