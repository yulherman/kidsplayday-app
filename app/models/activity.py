import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title_uk: Mapped[str] = mapped_column(String(300), nullable=False)
    title_en: Mapped[str] = mapped_column(String(300), nullable=False)
    short_description_uk: Mapped[str | None] = mapped_column(String(220), nullable=True)
    short_description_en: Mapped[str | None] = mapped_column(String(220), nullable=True)
    description_uk: Mapped[str] = mapped_column(Text, nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    instructions_uk: Mapped[str] = mapped_column(Text, nullable=False)
    instructions_en: Mapped[str] = mapped_column(Text, nullable=False)

    min_age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    max_age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    energy_level: Mapped[str] = mapped_column(String(20), nullable=False)  # calm, moderate, active
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # creative, science, sport, cooking, outdoor, social
    weather_type: Mapped[str] = mapped_column(String(20), default="any")  # any, indoor, outdoor
    materials_needed: Mapped[dict] = mapped_column(JSONB, default=list)
    developmental_goals: Mapped[list] = mapped_column(JSONB, default=list)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0)
    times_suggested: Mapped[int] = mapped_column(Integer, default=0)
    times_completed: Mapped[int] = mapped_column(Integer, default=0)
    times_liked: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserActivityHistory(Base):
    __tablename__ = "user_activity_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    activity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="suggested")  # suggested, completed, skipped, liked, disliked, try_later
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    suggested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    activity: Mapped["Activity"] = relationship()


class ActivityVerification(Base):
    __tablename__ = "activity_verifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), unique=True, nullable=False)
    verification_score: Mapped[float] = mapped_column(Float, default=0.0)
    verified_by: Mapped[str] = mapped_column(String(20), default="ai")  # ai, community
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ThemedWeek(Base):
    __tablename__ = "themed_weeks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title_uk: Mapped[str] = mapped_column(String(200), nullable=False)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    description_uk: Mapped[str] = mapped_column(Text, nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    target_age_min: Mapped[int] = mapped_column(Integer, nullable=False)
    target_age_max: Mapped[int] = mapped_column(Integer, nullable=False)
    day_plans: Mapped[dict] = mapped_column(JSONB, nullable=False)
    materials_shopping_list: Mapped[dict] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
