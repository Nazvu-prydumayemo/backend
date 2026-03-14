from typing import Any

from .errors import get_auth_error
from .schemas import ErrorResponse

LOGIN_REQUEST_BODY: dict[str, Any] = {
    "required": True,
    "content": {
        "application/json": {
            "schema": {
                "title": "LoginJsonRequest",
                "type": "object",
                "additionalProperties": False,
                "required": ["email", "password"],
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "example": "user@example.com",
                    },
                    "password": {
                        "type": "string",
                        "example": "string",
                    },
                },
            },
            "example": {
                "email": "user@example.com",
                "password": "string",
            },
        },
        "application/x-www-form-urlencoded": {
            "schema": {
                "title": "LoginFormRequest",
                "type": "object",
                "additionalProperties": False,
                "required": ["username", "password"],
                "properties": {
                    "username": {
                        "type": "string",
                        "format": "email",
                        "description": "OAuth2 username field. Use the user email.",
                        "example": "user@example.com",
                    },
                    "password": {
                        "type": "string",
                        "example": "string",
                    },
                    "grant_type": {
                        "type": "string",
                        "enum": ["password"],
                        "example": "password",
                    },
                    "scope": {
                        "type": "string",
                        "example": "",
                    },
                    "client_id": {
                        "type": "string",
                    },
                    "client_secret": {
                        "type": "string",
                    },
                },
            },
            "encoding": {
                "username": {"style": "form"},
                "password": {"style": "form"},
                "grant_type": {"style": "form"},
                "scope": {"style": "form"},
                "client_id": {"style": "form"},
                "client_secret": {"style": "form"},
            },
            "example": {
                "username": "user@example.com",
                "password": "string",
                "grant_type": "password",
                "scope": "",
            },
        },
    },
}


LOGIN_OPENAPI_EXTRA: dict[str, Any] = {
    "requestBody": LOGIN_REQUEST_BODY,
}


def _error_response(error_key: str, description: str) -> dict[str, Any]:
    error = get_auth_error(error_key)
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "example": {
                    "code": error.code,
                    "detail": error.detail,
                },
            },
        },
    }


def _error_response_with_examples(error_keys: list[str], description: str) -> dict[str, Any]:
    examples: dict[str, dict[str, Any]] = {}
    for key in error_keys:
        error = get_auth_error(key)
        examples[key] = {
            "summary": error.code,
            "value": {
                "code": error.code,
                "detail": error.detail,
            },
        }

    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "examples": examples,
            },
        },
    }


REGISTER_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: _error_response("email_already_registered", "Email already registered."),
    422: _error_response("request_validation_failed", "Request validation failed."),
    500: _error_response("user_creation_failed", "Unexpected server error while creating user."),
}


LOGIN_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: _error_response("invalid_credentials", "Authentication failed."),
    403: _error_response("inactive_user", "User account is inactive."),
    415: _error_response(
        "login_unsupported_content_type", "Unsupported content type. Use JSON or form-urlencoded."
    ),
    422: _error_response_with_examples(
        ["login_invalid_json_payload", "login_invalid_form_payload"],
        "Login payload validation failed.",
    ),
}


REFRESH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: _error_response("invalid_refresh_token", "Refresh token is invalid or expired."),
}


CURRENT_USER_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: _error_response("credentials_validation_failed", "Access token is missing or invalid."),
    403: _error_response("inactive_user", "Current user is inactive."),
}
