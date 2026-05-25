from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, children, materials, activities, themed_weeks
from app.api.premium import router as premium_router
from app.config import settings
from app.db.database import async_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session() as db:
        from app.services.seed_themed_weeks import seed_themed_weeks
        try:
            await seed_themed_weeks(db)
        except Exception as e:
            print(f"Seed skipped: {e}")
    yield


app = FastAPI(
    title="PlayDay API",
    description="AI-powered daily activity planner for kids 0-12",
    version="0.1.0",
    lifespan=lifespan,
)

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


@app.get("/health")
async def health():
    return {"status": "ok", "service": "playday-api"}
