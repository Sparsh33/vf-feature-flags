"""Pydantic models for auth domain (users, clients, requests, responses)."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    password_hash: str
    client_id: str
    role: str = "admin"
    created_at: datetime = Field(default_factory=_utcnow)
    is_deleted: bool = False


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    client_id: str
    role: str


class Client(BaseModel):
    id: Optional[str] = None
    name: str
    api_key_prefix: str
    api_key_hash: str
    created_at: datetime = Field(default_factory=_utcnow)
    is_deleted: bool = False


class ClientPublic(BaseModel):
    id: str
    name: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    client_name: str

    @field_validator("password")
    @classmethod
    def _password_min_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        return value

    @field_validator("client_name")
    @classmethod
    def _client_name_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("client_name must not be empty")
        return value.strip()


class SignupResponse(BaseModel):
    user: UserPublic
    client: ClientPublic
    api_key: str
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user: UserPublic
    access_token: str
    token_type: str = "bearer"


class RotateApiKeyResponse(BaseModel):
    api_key: str


class JWTPayload(BaseModel):
    sub: str
    client_id: str
    exp: int
