from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    language: str = "en"
    name: str | None = Field(default=None, max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AppleLoginRequest(BaseModel):
    identity_token: str
    name: str | None = Field(default=None, max_length=120)
    language: str = "en"


class UserResponse(BaseModel):
    id: UUID
    email: str
    language: str
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
