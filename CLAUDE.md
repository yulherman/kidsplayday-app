# CLAUDE.md

Project context for Claude Code. For complete agent guidance see [AGENTS.md](./AGENTS.md); for system design see [ARCHITECTURE.md](./ARCHITECTURE.md); for local setup see [README.md](./README.md).

## Critical rules

1. **Async only.** All DB access uses `AsyncSession` + `Depends(get_db)`. No sync SQLAlchemy anywhere.
2. **Bilingual content.** Every user-facing text field on `Activity` exists in both `_uk` and `_en`. New fields must follow the same pattern.
3. **Prompts live in `app/prompts/`.** Add a `.txt` file and load via `_load`/`_load_dir` in [app/prompts/__init__.py](app/prompts/__init__.py). Never inline prompt strings in Python.
4. **Auth via dependency.** Protected routes use `Depends(get_current_user)` from [app/core/dependencies.py](app/core/dependencies.py). Don't write custom auth.
5. **Structured OpenAI output.** Use `ACTIVITY_RESPONSE_SCHEMA` in [app/services/ai_engine.py](app/services/ai_engine.py); never parse free-form text from the model.

## Quick start

```bash
docker-compose up -d --build
docker-compose exec api alembic upgrade head
curl http://localhost:8000/health
```
