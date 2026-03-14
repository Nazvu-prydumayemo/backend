from dataclasses import dataclass
from typing import NoReturn

from fastapi import status


@dataclass(frozen=True)
class AuthErrorDefinition:
    status_code: int
    code: str
    detail: str
    headers: dict[str, str] | None = None


AUTH_ERRORS: dict[str, AuthErrorDefinition] = {
    "invalid_credentials": AuthErrorDefinition(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="AUTH_INVALID_CREDENTIALS",
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    ),
    "credentials_validation_failed": AuthErrorDefinition(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="AUTH_CREDENTIALS_VALIDATION_FAILED",
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    ),
    "inactive_user": AuthErrorDefinition(
        status_code=status.HTTP_403_FORBIDDEN,
        code="AUTH_INACTIVE_USER",
        detail="Inactive user",
    ),
    "invalid_token_type": AuthErrorDefinition(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="AUTH_INVALID_TOKEN_TYPE",
        detail="Invalid token type",
    ),
    "invalid_refresh_token": AuthErrorDefinition(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="AUTH_INVALID_REFRESH_TOKEN",
        detail="Invalid refresh token",
    ),
    "login_invalid_json_payload": AuthErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="AUTH_LOGIN_INVALID_JSON_PAYLOAD",
        detail="Invalid JSON login payload",
    ),
    "login_invalid_form_payload": AuthErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="AUTH_LOGIN_INVALID_FORM_PAYLOAD",
        detail="Invalid login form payload",
    ),
    "request_validation_failed": AuthErrorDefinition(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="REQUEST_VALIDATION_ERROR",
        detail="Request validation failed",
    ),
    "login_unsupported_content_type": AuthErrorDefinition(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        code="AUTH_LOGIN_UNSUPPORTED_CONTENT_TYPE",
        detail="Unsupported Content-Type for login",
    ),
    "email_already_registered": AuthErrorDefinition(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="AUTH_EMAIL_ALREADY_REGISTERED",
        detail="Email already registered",
    ),
    "user_creation_failed": AuthErrorDefinition(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="AUTH_USER_CREATION_FAILED",
        detail="Could not create user",
    ),
    "forbidden_resource": AuthErrorDefinition(
        status_code=status.HTTP_403_FORBIDDEN,
        code="AUTH_FORBIDDEN_RESOURCE",
        detail="You do not have permission to access this resource",
    ),
}


class AuthAPIException(Exception):
    def __init__(self, error_key: str, detail_override: str | None = None):
        if error_key not in AUTH_ERRORS:
            raise ValueError(f"Unknown auth error key: {error_key}")

        definition = AUTH_ERRORS[error_key]
        self.status_code = definition.status_code
        self.code = definition.code
        self.detail = detail_override or definition.detail
        self.headers = definition.headers

    def as_payload(self) -> dict[str, str]:
        return {
            "code": self.code,
            "detail": self.detail,
        }


def get_auth_error(error_key: str) -> AuthErrorDefinition:
    if error_key not in AUTH_ERRORS:
        raise ValueError(f"Unknown auth error key: {error_key}")
    return AUTH_ERRORS[error_key]


def raise_auth_error(error_key: str, detail_override: str | None = None) -> NoReturn:
    raise AuthAPIException(error_key=error_key, detail_override=detail_override)
