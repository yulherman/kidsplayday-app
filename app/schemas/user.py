from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


SUPPORTED_LANGUAGES = {"uk", "en", "fr", "de", "es", "it"}


def _normalize_language(v: str | None) -> str:
    if not v:
        return "en"
    code = v.lower()[:2]
    return code if code in SUPPORTED_LANGUAGES else "en"


def _normalize_country(v: str | None) -> str | None:
    if not v:
        return None
    return v.upper()[:2]


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    language: str = "en"
    country: str | None = Field(default=None, min_length=2, max_length=2)
    name: str | None = Field(default=None, max_length=120)

    @field_validator("language")
    @classmethod
    def _check_language(cls, v: str) -> str:
        return _normalize_language(v)

    @field_validator("country")
    @classmethod
    def _check_country(cls, v: str | None) -> str | None:
        return _normalize_country(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AppleLoginRequest(BaseModel):
    identity_token: str
    name: str | None = Field(default=None, max_length=120)
    language: str = "en"
    country: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("language")
    @classmethod
    def _check_language(cls, v: str) -> str:
        return _normalize_language(v)

    @field_validator("country")
    @classmethod
    def _check_country(cls, v: str | None) -> str | None:
        return _normalize_country(v)


class UserResponse(BaseModel):
    id: UUID
    email: str
    language: str
    country: str | None = None
    is_premium: bool
    name: str | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LocationUpdate(BaseModel):
    latitude: float
    longitude: float


class LanguageUpdate(BaseModel):
    language: str

    @field_validator("language")
    @classmethod
    def _check_language(cls, v: str) -> str:
        return _normalize_language(v)


class CountryUpdate(BaseModel):
    country: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("country")
    @classmethod
    def _check_country(cls, v: str | None) -> str | None:
        return _normalize_country(v)


class ChildCreate(BaseModel):
    birth_date: date


class ChildResponse(BaseModel):
    id: UUID
    birth_date: date
    age_months: int
    age_category: str

    model_config = {"from_attributes": True}


class MaterialUpdate(BaseModel):
    material_name: str
    category: str
    is_available: bool = True


class MaterialBatchUpdate(BaseModel):
    materials: list[MaterialUpdate]
