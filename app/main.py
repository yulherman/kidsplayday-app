import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

from app.api import auth, children, materials, activities, themed_weeks
from app.api.premium import router as premium_router
from app.api.push import router as push_router
from app.api.referrals import router as referrals_router
from app.api.streak import router as streak_router
from app.config import settings
from app.db.database import async_session, engine
from app.pages import PRIVACY_HTML, SUPPORT_HTML
from app.services import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session() as db:
        from app.services.seed_themed_weeks import seed_themed_weeks
        try:
            await seed_themed_weeks(db)
        except Exception as e:
            logger.warning("Seed skipped: %s", e)

    scheduler_tasks: list = []
    scheduler.start(scheduler_tasks)
    try:
        yield
    finally:
        for task in scheduler_tasks:
            task.cancel()
        await engine.dispose()


app = FastAPI(
    title="Kids Activities API",
    description="AI-powered daily activity planner for kids 0-12",
    version="0.1.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(children.router)
app.include_router(materials.router)
app.include_router(activities.router)
app.include_router(themed_weeks.router)
app.include_router(premium_router)
app.include_router(push_router)
app.include_router(streak_router)
app.include_router(referrals_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "playday-api"}


@app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def privacy():
    return HTMLResponse(PRIVACY_HTML)


@app.get("/support", response_class=HTMLResponse, include_in_schema=False)
async def support():
    return HTMLResponse(SUPPORT_HTML)
