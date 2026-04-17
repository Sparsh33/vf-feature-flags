"""Auth domain business logic: signup, login, token issue, API key rotation."""

from typing import Optional, Tuple

from pymongo.errors import DuplicateKeyError

from app.common.errors import ConflictError, InvalidApiKey, InvalidCredentials, UserNotFound
from app.common.logging_helpers import LoggingData, log_error, log_info
from app.services.auth.auth_model import (
    Client,
    ClientPublic,
    LoginRequest,
    LoginResponse,
    RotateApiKeyResponse,
    SignupRequest,
    SignupResponse,
    User,
    UserPublic,
)
from app.services.auth.repositories.client_repository import ClientRepository
from app.services.auth.repositories.user_repository import UserRepository
from app.services.auth.security import (
    api_key_prefix,
    create_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_api_key,
    verify_password,
)
from app.services.auth.transactional import transactional

# Pre-computed bcrypt hash of a fixed throwaway password. Running verify_password
# against it when the email is unknown keeps login-path CPU cost constant and
# closes the timing-oracle that leaks account existence.
_DUMMY_PASSWORD_HASH = hash_password("__vf_ff_dummy_password_for_constant_time__")


class AuthService:
    def __init__(
        self,
        user_repository: Optional[UserRepository] = None,
        client_repository: Optional[ClientRepository] = None,
    ) -> None:
        self._users = user_repository or UserRepository()
        self._clients = client_repository or ClientRepository()

    @transactional
    async def signup(self, request: SignupRequest) -> SignupResponse:
        plaintext_key = generate_api_key()
        client_record = Client(
            name=request.client_name,
            api_key_prefix=api_key_prefix(plaintext_key),
            api_key_hash=hash_api_key(plaintext_key),
        )
        client_record = await self._clients.insert(client_record)
        try:
            user_record = User(
                email=request.email,
                password_hash=hash_password(request.password),
                client_id=client_record.id or "",
            )
            user_record = await self._users.insert(user_record)
        except DuplicateKeyError as exc:
            await self._clients.delete_by_id(client_record.id or "")
            log_error(
                LoggingData(
                    message="signup.duplicate_email",
                    error=exc,
                )
            )
            raise ConflictError("email already registered") from exc
        except Exception as exc:
            await self._clients.delete_by_id(client_record.id or "")
            log_error(LoggingData(message="signup failed", error=exc))
            raise
        token = create_access_token(user_id=user_record.id or "", client_id=client_record.id or "")
        log_info(
            LoggingData(
                message="user signed up",
                context={"user_id": user_record.id, "client_id": client_record.id},
            )
        )
        return SignupResponse(
            user=self._to_public_user(user_record),
            client=ClientPublic(id=client_record.id or "", name=client_record.name),
            api_key=plaintext_key,
            access_token=token,
        )

    async def login(self, request: LoginRequest) -> LoginResponse:
        user_record = await self._users.find_by_email(request.email)
        # Run bcrypt regardless of whether the user exists to keep the response
        # time constant. This closes the timing-oracle that would otherwise leak
        # account existence to an attacker enumerating emails.
        candidate_hash = user_record.password_hash if user_record else _DUMMY_PASSWORD_HASH
        password_ok = verify_password(request.password, candidate_hash)
        if user_record is None or not password_ok:
            log_error(LoggingData(message="login.invalid_credentials"))
            raise InvalidCredentials("invalid email or password")
        token = create_access_token(user_id=user_record.id or "", client_id=user_record.client_id)
        return LoginResponse(user=self._to_public_user(user_record), access_token=token)

    async def get_user_public(self, user_id: str) -> UserPublic:
        user_record = await self._users.find_by_id(user_id)
        if user_record is None:
            raise UserNotFound(f"user {user_id} not found")
        return self._to_public_user(user_record)

    async def rotate_api_key(self, client_id: str) -> RotateApiKeyResponse:
        plaintext_key = generate_api_key()
        new_prefix = api_key_prefix(plaintext_key)
        new_hash = hash_api_key(plaintext_key)
        updated = await self._clients.update_api_key(client_id, new_prefix, new_hash)
        if not updated:
            raise UserNotFound(f"client {client_id} not found")
        log_info(LoggingData(message="api key rotated", context={"client_id": client_id}))
        return RotateApiKeyResponse(api_key=plaintext_key)

    async def resolve_client_by_api_key(self, plaintext_key: str) -> Tuple[Client, ClientPublic]:
        if not plaintext_key or len(plaintext_key) < 8:
            raise InvalidApiKey("invalid api key")
        prefix = api_key_prefix(plaintext_key)
        candidates = await self._clients.find_candidates_by_prefix(prefix)
        for candidate in candidates:
            if verify_api_key(plaintext_key, candidate.api_key_hash):
                return candidate, ClientPublic(id=candidate.id or "", name=candidate.name)
        raise InvalidApiKey("invalid api key")

    def _to_public_user(self, user_record: User) -> UserPublic:
        return UserPublic(
            id=user_record.id or "",
            email=user_record.email,
            client_id=user_record.client_id,
            role=user_record.role,
        )
