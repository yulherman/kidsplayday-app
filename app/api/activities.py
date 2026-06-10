import asyncio
import hashlib
import uuid
import logging
from datetime import date, datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.services.pdf_renderer import render_activity_pdf

from app.api.premium import check_premium_or_limit
from app.services.plan_quota import assert_plan_quota, increment_plan_quota
from app.core.dependencies import get_current_user
from app.db.database import async_session, get_db
from app.models.activity import Activity, ActivityVerification, UserActivityHistory
from app.models.user import Child, HomeMaterial, User
from app.schemas.activity import (
    ActivityResponse,
    ByMaterialsRequest,
    ByThemeRequest,
    DayPlanResponse,
    EmergencyRequest,
    GeneratePlanRequest,
    HistoryItemResponse,
    RateActivityRequest,
)
from app.services.ai_engine import (
    ActivityGenerationError,
    determine_mode,
    generate_activities,
    get_num_activities,
)
from app.services.streak import update_streak
from app.services.verification import ai_verify_activity
from app.services.weather import get_weather

router = APIRouter(prefix="/activities", tags=["activities"])
logger = logging.getLogger(__name__)


def _normalize_location(location: str | None) -> str | None:
    if location is None:
        return None
    normalized = location.strip()
    if not normalized:
        return None
    return normalized.lower()


async def _get_children_info(db: AsyncSession, user: User, child_ids: list[uuid.UUID]) -> list[dict]:
    result = await db.execute(
        select(Child).where(Child.user_id == user.id, Child.id.in_(child_ids))
    )
    children = result.scalars().all()
    if not children:
        raise HTTPException(status_code=404, detail="No children found")
    return [{"age_months": c.age_months, "age_category": c.age_category, "id": c.id} for c in children]


async def _get_user_materials(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(HomeMaterial.material_name).where(
            HomeMaterial.user_id == user_id, HomeMaterial.is_available.is_(True)
        )
    )
    return [r[0] for r in result.all()]


async def _get_excluded_titles(db: AsyncSession, user_id: uuid.UUID, limit: int = 50) -> list[str]:
    result = await db.execute(
        select(Activity.title)
        .join(UserActivityHistory, UserActivityHistory.activity_id == Activity.id)
        .where(UserActivityHistory.user_id == user_id)
        .order_by(UserActivityHistory.suggested_at.desc())
        .limit(limit)
    )
    return [r[0] for r in result.all()]


async def _empty_list() -> list:
    return []


async def _resolve_materials(
    db: AsyncSession,
    user_id: uuid.UUID,
    materials_filter: list[str] | None,
) -> list[str]:
    if materials_filter is not None:
        return materials_filter
    return await _get_user_materials(db, user_id)


async def _fetch_weather(user: User, location: str | None) -> dict | None:
    if location == "outdoor" and (not user.location_lat or not user.location_lng):
        raise HTTPException(
            status_code=400,
            detail="Outdoor activities require user location. Please set location first.",
        )
    if user.location_lat and user.location_lng:
        return await get_weather(user.location_lat, user.location_lng)
    return None


async def _get_favorite_titles(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(Activity.title)
        .join(UserActivityHistory, UserActivityHistory.activity_id == Activity.id)
        .where(
            UserActivityHistory.user_id == user_id,
            UserActivityHistory.status.in_(["liked", "completed"]),
        )
        .order_by(UserActivityHistory.suggested_at.desc())
        .limit(10)
    )
    return [r[0] for r in result.all()]


async def _get_fallback_activities(
    db: AsyncSession,
    user_id: uuid.UUID,
    youngest_age_months: int,
    limit: int,
) -> list[Activity]:
    history_subquery = (
        select(UserActivityHistory.activity_id)
        .where(UserActivityHistory.user_id == user_id)
    )
    result = await db.execute(
        select(Activity)
        .where(
            Activity.min_age_months <= youngest_age_months,
            Activity.max_age_months >= youngest_age_months,
            Activity.is_verified.is_(True),
            Activity.id.notin_(history_subquery),
        )
        .order_by(Activity.avg_rating.desc(), Activity.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def _link_existing_activities(
    db: AsyncSession,
    activities: list[Activity],
    user_id: uuid.UUID,
    child_ids: list[uuid.UUID],
) -> None:
    for activity in activities:
        activity.times_suggested += 1
        for child_id in child_ids:
            db.add(UserActivityHistory(
                user_id=user_id,
                child_id=child_id,
                activity_id=activity.id,
                status="suggested",
            ))
    await db.flush()


async def _save_activities(
    db: AsyncSession,
    activities_data: list[dict],
    user_id: uuid.UUID,
    child_ids: list[uuid.UUID],
) -> tuple[list[Activity], list[tuple[uuid.UUID, dict]]]:
    saved = []
    verify_queue: list[tuple[uuid.UUID, dict]] = []
    _VALID_ENERGY = {"calm", "moderate", "active"}
    _VALID_WEATHER = {"any", "indoor", "outdoor"}

    for act_data in activities_data:
        energy_raw = act_data.get("energy_level", "moderate")
        weather_raw = act_data.get("weather_type", "any")
        activity = Activity(
            title=act_data.get("title", ""),
            short_description=act_data.get("short_description", ""),
            description=act_data.get("description", ""),
            instructions=act_data.get("instructions", ""),
            language=act_data.get("language", "uk"),
            min_age_months=act_data.get("min_age_months", 0),
            max_age_months=act_data.get("max_age_months", 144),
            duration_minutes=act_data.get("duration_minutes", 30),
            energy_level=energy_raw if energy_raw in _VALID_ENERGY else "moderate",
            category=act_data.get("category", "creative"),
            weather_type=weather_raw if weather_raw in _VALID_WEATHER else "any",
            materials_needed=act_data.get("materials_needed", []),
            developmental_goals=act_data.get("developmental_goals", []),
            times_suggested=1,
        )
        db.add(activity)
        await db.flush()

        # Save immediately with a neutral verification score;
        # expensive AI verification runs in background after response.
        verification_score = 0.7
        db.add(ActivityVerification(
            activity_id=activity.id,
            verification_score=verification_score,
            verified_by="ai",
        ))
        activity.is_verified = verification_score >= 0.7
        verify_queue.append((activity.id, act_data))

        for child_id in child_ids:
            db.add(UserActivityHistory(
                user_id=user_id,
                child_id=child_id,
                activity_id=activity.id,
                status="suggested",
            ))

        saved.append(activity)

    await db.flush()
    return saved, verify_queue



async def _verify_activities_background(items: list[tuple[uuid.UUID, dict]]) -> None:
    if not items:
        return

    async with async_session() as db:
        for activity_id, act_data in items:
            try:
                verification_score = await ai_verify_activity(act_data)
                verification_result = await db.execute(
                    select(ActivityVerification).where(ActivityVerification.activity_id == activity_id)
                )
                verification = verification_result.scalar_one_or_none()
                if verification:
                    verification.verification_score = verification_score
                activity_result = await db.execute(select(Activity).where(Activity.id == activity_id))
                activity = activity_result.scalar_one_or_none()
                if activity:
                    activity.is_verified = verification_score >= 0.7
            except Exception:
                logger.exception("Background verification failed for activity_id=%s", activity_id)
        await db.commit()


@router.post("/generate-plan", response_model=DayPlanResponse)
async def generate_plan(
    data: GeneratePlanRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_premium_or_limit(user, db)
    await assert_plan_quota(user)
    lang = data.language or user.language
    location = _normalize_location(data.location)
    children_info, materials, excluded, favorites, weather = await asyncio.gather(
        _get_children_info(db, user, data.child_ids),
        _resolve_materials(db, user.id, data.materials_filter),
        _get_excluded_titles(db, user.id),
        _get_favorite_titles(db, user.id) if data.mix_favorites else _empty_list(),
        _fetch_weather(user, location),
    )

    youngest = min(c["age_months"] for c in children_info)
    today = date.today()
    mode = determine_mode(youngest, data.is_vacation, today.weekday())
    num = get_num_activities(mode)

    try:
        activities_data = await generate_activities(
            children_info=children_info,
            num_activities=num,
            available_time=data.available_time_minutes,
            weather=weather,
            materials=materials,
            energy_level=data.energy_level,
            theme=data.theme,
            favorite_titles=favorites,
            mix_favorites=data.mix_favorites,
            excluded_titles=excluded,
            mode=mode,
            location=location,
            language=lang,
        )
    except ActivityGenerationError as exc:
        logger.error("Plan generation failed for user=%s reason=%s", user.id, exc.internal_reason)
        activities_data = []

    if activities_data:
        saved, verify_queue = await _save_activities(db, activities_data, user.id, data.child_ids)
        background_tasks.add_task(_verify_activities_background, verify_queue)
    else:
        logger.warning("AI produced no safe activities, using DB fallback user=%s", user.id)
        saved = await _get_fallback_activities(db, user.id, youngest, num)
        if not saved:
            raise HTTPException(
                status_code=502,
                detail="No safe activities available right now. Please try again later.",
            )
        await _link_existing_activities(db, saved, user.id, data.child_ids)

    await db.commit()
    await increment_plan_quota(user)
    return DayPlanResponse(
        date=today.isoformat(),
        weather=weather["description"] if weather else None,
        temperature=weather["temperature"] if weather else None,
        mode=mode,
        activities=[ActivityResponse.model_validate(a) for a in saved],
    )


@router.post("/emergency", response_model=DayPlanResponse)
async def emergency_activities(
    data: EmergencyRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_premium_or_limit(user, db)
    await assert_plan_quota(user)
    lang = data.language or user.language
    children_info, materials = await asyncio.gather(
        _get_children_info(db, user, data.child_ids),
        _get_user_materials(db, user.id),
    )

    try:
        activities_data = await generate_activities(
            children_info=children_info,
            num_activities=3,
            available_time=data.max_duration_minutes,
            materials=materials,
            mode="daily",
            language=lang,
        )
    except ActivityGenerationError as exc:
        logger.error("Emergency generation failed for user=%s reason=%s", user.id, exc.internal_reason)
        activities_data = []

    if activities_data:
        saved, verify_queue = await _save_activities(db, activities_data, user.id, data.child_ids)
        background_tasks.add_task(_verify_activities_background, verify_queue)
    else:
        youngest = min(c["age_months"] for c in children_info)
        logger.warning("AI emergency produced no safe activities, using DB fallback user=%s", user.id)
        saved = await _get_fallback_activities(db, user.id, youngest, 3)
        if not saved:
            raise HTTPException(
                status_code=502,
                detail="No safe emergency activities available right now. Please try again later.",
            )
        await _link_existing_activities(db, saved, user.id, data.child_ids)

    await db.commit()
    await increment_plan_quota(user)
    return DayPlanResponse(
        date=date.today().isoformat(),
        mode="emergency",
        activities=[ActivityResponse.model_validate(a) for a in saved],
    )


@router.post("/by-materials", response_model=DayPlanResponse)
async def generate_by_materials(
    data: ByMaterialsRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_premium_or_limit(user, db)
    await assert_plan_quota(user)
    lang = data.language or user.language
    location = _normalize_location(data.location)
    children_info, excluded, weather = await asyncio.gather(
        _get_children_info(db, user, data.child_ids),
        _get_excluded_titles(db, user.id),
        _fetch_weather(user, location),
    )

    try:
        activities_data = await generate_activities(
            children_info=children_info,
            num_activities=4,
            materials=data.materials,
            theme=data.theme,
            weather=weather,
            excluded_titles=excluded,
            mode="daily",
            location=location,
            language=lang,
        )
    except ActivityGenerationError as exc:
        logger.error("By-materials generation failed for user=%s reason=%s", user.id, exc.internal_reason)
        activities_data = []

    if activities_data:
        saved, verify_queue = await _save_activities(db, activities_data, user.id, data.child_ids)
        background_tasks.add_task(_verify_activities_background, verify_queue)
    else:
        youngest = min(c["age_months"] for c in children_info)
        logger.warning("AI by-materials produced no safe activities, using DB fallback user=%s", user.id)
        saved = await _get_fallback_activities(db, user.id, youngest, 4)
        if not saved:
            raise HTTPException(
                status_code=502,
                detail="No safe activities available for selected materials. Please try different filters.",
            )
        await _link_existing_activities(db, saved, user.id, data.child_ids)

    await db.commit()
    await increment_plan_quota(user)
    return DayPlanResponse(
        date=date.today().isoformat(),
        mode="by_materials",
        activities=[ActivityResponse.model_validate(a) for a in saved],
    )


@router.post("/by-theme", response_model=DayPlanResponse)
async def generate_by_theme(
    data: ByThemeRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_premium_or_limit(user, db)
    await assert_plan_quota(user)
    lang = data.language or user.language
    location = _normalize_location(data.location)
    children_info, materials, excluded, weather = await asyncio.gather(
        _get_children_info(db, user, data.child_ids),
        _get_user_materials(db, user.id),
        _get_excluded_titles(db, user.id),
        _fetch_weather(user, location),
    )

    try:
        activities_data = await generate_activities(
            children_info=children_info,
            num_activities=4,
            materials=materials,
            theme=data.theme,
            weather=weather,
            excluded_titles=excluded,
            mode="daily",
            location=location,
            language=lang,
        )
    except ActivityGenerationError as exc:
        logger.error("By-theme generation failed for user=%s reason=%s", user.id, exc.internal_reason)
        activities_data = []

    if activities_data:
        saved, verify_queue = await _save_activities(db, activities_data, user.id, data.child_ids)
        background_tasks.add_task(_verify_activities_background, verify_queue)
    else:
        youngest = min(c["age_months"] for c in children_info)
        logger.warning("AI by-theme produced no safe activities, using DB fallback user=%s", user.id)
        saved = await _get_fallback_activities(db, user.id, youngest, 4)
        if not saved:
            raise HTTPException(
                status_code=502,
                detail="No safe activities available for selected theme. Please try another theme.",
            )
        await _link_existing_activities(db, saved, user.id, data.child_ids)

    await db.commit()
    await increment_plan_quota(user)
    return DayPlanResponse(
        date=date.today().isoformat(),
        mode="by_theme",
        activities=[ActivityResponse.model_validate(a) for a in saved],
    )


@router.post("/{activity_id}/rate")
async def rate_activity(
    activity_id: uuid.UUID,
    data: RateActivityRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    history_where = [
        UserActivityHistory.user_id == user.id,
        UserActivityHistory.activity_id == activity_id,
    ]
    if data.child_id:
        history_where.append(UserActivityHistory.child_id == data.child_id)
    result = await db.execute(
        select(UserActivityHistory).where(*history_where)
        .order_by(UserActivityHistory.suggested_at.desc())
    )
    history = result.scalars().first()
    if not history:
        raise HTTPException(status_code=404, detail="Activity not in your history")

    history.status = data.status
    history.rating = data.rating
    history.notes = data.notes
    if data.status == "completed":
        history.completed_at = datetime.now(timezone.utc)

    activity_result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = activity_result.scalar_one_or_none()
    if activity:
        if data.status == "completed":
            activity.times_completed += 1
        if data.status == "liked":
            activity.times_liked += 1
        if data.rating:
            total_ratings = await db.execute(
                select(func.count(), func.avg(UserActivityHistory.rating)).where(
                    UserActivityHistory.activity_id == activity_id,
                    UserActivityHistory.rating.isnot(None),
                )
            )
            row = total_ratings.one()
            activity.avg_rating = float(row[1]) if row[1] else 0.0

    if data.status == "completed":
        await update_streak(db, user.id, date.today(), user.language)

    return {"status": "ok"}


async def _get_deduped_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: str | None = None,
    statuses: list[str] | None = None,
    category: str | None = None,
    child_ids: list[uuid.UUID] | None = None,
    limit: int | None = None,
) -> list[UserActivityHistory]:
    """Return one history row per activity (most recent by suggested_at)."""
    count_result = await db.execute(
        select(func.count()).select_from(UserActivityHistory)
        .where(UserActivityHistory.user_id == user_id)
    )
    logger.info(
        "history query user_id=%s child_ids=%s total_user_rows=%s status=%s",
        user_id, child_ids, count_result.scalar(), status,
    )

    ranked = (
        select(
            UserActivityHistory.id.label("history_id"),
            func.row_number()
            .over(
                partition_by=UserActivityHistory.activity_id,
                order_by=UserActivityHistory.suggested_at.desc(),
            )
            .label("rn"),
        )
        .where(UserActivityHistory.user_id == user_id)
    )
    if child_ids:
        if len(child_ids) == 1:
            ranked = ranked.where(UserActivityHistory.child_id == child_ids[0])
        else:
            common_activity_ids = (
                select(UserActivityHistory.activity_id)
                .where(
                    UserActivityHistory.user_id == user_id,
                    UserActivityHistory.child_id.in_(child_ids),
                )
                .group_by(UserActivityHistory.activity_id)
                .having(
                    func.count(func.distinct(UserActivityHistory.child_id)) == len(child_ids)
                )
            )
            ranked = ranked.where(
                UserActivityHistory.child_id.in_(child_ids),
                UserActivityHistory.activity_id.in_(common_activity_ids),
            )
    if status:
        ranked = ranked.where(UserActivityHistory.status == status)
    if statuses:
        ranked = ranked.where(UserActivityHistory.status.in_(statuses))
    if category:
        ranked = ranked.join(Activity).where(Activity.category == category)

    ranked_subq = ranked.subquery()
    query = (
        select(UserActivityHistory)
        .options(selectinload(UserActivityHistory.activity))
        .join(ranked_subq, UserActivityHistory.id == ranked_subq.c.history_id)
        .where(ranked_subq.c.rn == 1)
        .order_by(UserActivityHistory.suggested_at.desc())
    )
    # str(query.compile(compile_kwargs={"literal_binds": True}))
    if limit is not None:
        query = query.limit(limit)

    result = await db.execute(query)
    to_list = list(result.scalars().all())
    return to_list


@router.get("/favorites", response_model=list[HistoryItemResponse])
async def get_favorites(
    child_ids: list[uuid.UUID] | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_deduped_history(
        db,
        user.id,
        statuses=["liked", "completed"],
        child_ids=child_ids,
    )


@router.get("/not-tried", response_model=list[ActivityResponse])
async def get_not_tried(
    child_ids: list[uuid.UUID] | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activities that exist in DB but were never suggested to this user (or selected children)."""
    tried_query = (
        select(UserActivityHistory.activity_id)
        .where(UserActivityHistory.user_id == user.id)
    )
    if child_ids:
        tried_query = tried_query.where(UserActivityHistory.child_id.in_(child_ids))
    result = await db.execute(
        select(Activity)
        .where(
            Activity.id.notin_(tried_query),
            Activity.is_verified.is_(True),
            Activity.avg_rating >= 3.0,
        )
        .order_by(Activity.avg_rating.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.get("/history", response_model=list[HistoryItemResponse])
async def get_history(
    status: str | None = None,
    category: str | None = None,
    child_ids: list[uuid.UUID] | None = Query(None),
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_deduped_history(
        db,
        user.id,
        status=status,
        category=category,
        child_ids=child_ids,
        limit=limit,
    )


PDF_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


def _pdf_cache_key(activity_id: uuid.UUID, ref_code: str | None) -> str:
    ref_hash = hashlib.sha1((ref_code or "").encode()).hexdigest()[:10]
    return f"pdf:{activity_id}:{ref_hash}"


@router.get("/{activity_id}/activity.pdf")
async def get_activity_pdf(
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    ref_code = user.referral_code
    cache_key = _pdf_cache_key(activity_id, ref_code)

    redis_client: aioredis.Redis | None = None
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)
        cached = await redis_client.get(cache_key)
        if cached:
            return Response(content=cached, media_type="application/pdf")
    except Exception:
        logger.exception("Redis PDF cache read failed")
        cached = None

    lang = activity.language
    materials_raw = activity.materials_needed or []
    materials = [m if isinstance(m, str) else m.get("name", "") for m in materials_raw]
    materials = [m for m in materials if m]
    goals = [g for g in (activity.developmental_goals or []) if isinstance(g, str) and g]

    share_url = settings.share_landing_url
    if ref_code:
        sep = "&" if "?" in share_url else "?"
        share_url = f"{share_url}{sep}ref={ref_code}"

    pdf_bytes = await asyncio.to_thread(
        render_activity_pdf,
        title=activity.title,
        description=activity.description or "",
        instructions=activity.instructions or "",
        materials=materials,
        goals=goals,
        category=activity.category,
        energy_level=activity.energy_level,
        duration_minutes=activity.duration_minutes,
        min_age_months=activity.min_age_months,
        max_age_months=activity.max_age_months,
        share_url=share_url,
        lang=lang,
    )

    if redis_client is not None:
        try:
            await redis_client.set(cache_key, pdf_bytes, ex=PDF_CACHE_TTL_SECONDS)
        except Exception:
            logger.exception("Redis PDF cache write failed")
        finally:
            await redis_client.aclose()

    return Response(content=pdf_bytes, media_type="application/pdf")
