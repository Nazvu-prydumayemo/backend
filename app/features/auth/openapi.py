from typing import Any

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
