"""Custom exception classes raised by services. Controllers map these to HTTP."""


class AppError(Exception):
    """Base class for domain errors."""


class NotFoundError(AppError):
    pass


class FlagNotFound(NotFoundError):
    pass


class ClientNotFound(NotFoundError):
    pass


class UserNotFound(NotFoundError):
    pass


class ValidationError(AppError):
    pass


class InvalidCohortSum(ValidationError):
    """Raised when cohort weights don't sum to 100."""


class InvalidRuleConfig(ValidationError):
    pass


class AuthError(AppError):
    pass


class InvalidCredentials(AuthError):
    pass


class InvalidApiKey(AuthError):
    pass


class PermissionDenied(AuthError):
    pass


class ConflictError(AppError):
    pass


class DuplicateFlagKey(ConflictError):
    pass


class FlagAlreadyExists(ConflictError):
    pass


class DuplicateEmail(ConflictError):
    pass


class AuditError(AppError):
    pass


class AnalyticsError(AppError):
    pass


class NLSessionError(AppError):
    pass


class NLSessionNotFound(NotFoundError):
    pass


class EvalError(AppError):
    pass
