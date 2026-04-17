"""Password hashing, API key generation, and JWT encode/decode helpers."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.settings import settings
from app.services.auth.auth_model import JWTPayload

JWT_ALGORITHM = "HS256"
API_KEY_PREFIX_LENGTH = 8

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _pwd_context.verify(plain_password, password_hash)
    except ValueError:
        return False


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def api_key_prefix(plaintext_key: str) -> str:
    return plaintext_key[:API_KEY_PREFIX_LENGTH]


def hash_api_key(plaintext_key: str) -> str:
    return _pwd_context.hash(plaintext_key)


def verify_api_key(plaintext_key: str, key_hash: str) -> bool:
    try:
        return _pwd_context.verify(plaintext_key, key_hash)
    except ValueError:
        return False


def create_access_token(user_id: str, client_id: str) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_ttl_minutes)
    payload = {"sub": user_id, "client_id": client_id, "exp": int(expire_at.timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[JWTPayload]:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    sub = data.get("sub")
    client_id = data.get("client_id")
    exp = data.get("exp")
    if not sub or not client_id or exp is None:
        return None
    return JWTPayload(sub=sub, client_id=client_id, exp=int(exp))
