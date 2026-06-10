from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class GeneratePlanRequest(BaseModel):
    child_ids: list[UUID]
    available_time_minutes: int = 120
    energy_level: str | None = None  # calm, moderate, active
    theme: str | None = None
    materials_filter: list[str] | None = None
    location: str | None = None  # home, cafe, outdoor
    mix_favorites: bool = False
    is_vacation: bool = False
    language: str | None = None


class EmergencyRequest(BaseModel):
    child_ids: list[UUID]
    max_duration_minutes: int = 10
    language: str | None = None


class ByMaterialsRequest(BaseModel):
    child_ids: list[UUID]
    materials: list[str]
    theme: str | None = None
    location: str | None = None  # home, cafe, outdoor
    language: str | None = None


class ByThemeRequest(BaseModel):
    child_ids: list[UUID]
    theme: str
    location: str | None = None  # home, cafe, outdoor
    language: str | None = None


class ActivityResponse(BaseModel):
    id: UUID
    title: str
    short_description: str | None = None
    description: str
    instructions: str
    language: str = "uk"
    min_age_months: int
    max_age_months: int
    duration_minutes: int
    energy_level: str
    category: str
    weather_type: str
    materials_needed: list[str]
    developmental_goals: list[str]
    avg_rating: float
    is_verified: bool

    model_config = {"from_attributes": True}

    @field_validator("materials_needed", "developmental_goals", mode="before")
    @classmethod
    def ensure_list_fields(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class DayPlanResponse(BaseModel):
    date: str
    weather: str | None = None
    temperature: float | None = None
    mode: str  # daily, evening, weekend, vacation
    activities: list[ActivityResponse]


class RateActivityRequest(BaseModel):
    status: str  # completed, skipped, liked, disliked, try_later
    child_id: UUID | None = None
    rating: int | None = None  # 1-5
    notes: str | None = None


class HistoryItemResponse(BaseModel):
    id: UUID
    activity: ActivityResponse
    status: str
    rating: int | None
    suggested_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ThemedWeekResponse(BaseModel):
    id: UUID
    title_uk: str
    title_en: str
    description_uk: str
    description_en: str
    target_age_min: int
    target_age_max: int
    day_plans: dict
    materials_shopping_list: list[str]

    model_config = {"from_attributes": True}
