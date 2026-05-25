"""Unit tests for auth service layer."""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_refresh_token
from app.features.auth.service import (
    confirm_password_reset,
    login_user,
    refresh_access_token,
    register_user,
    request_password_reset,
    verify_reset_code,
)
from app.features.user.schemas import UserCreate, UserRoleEnum
from app.features.user.service import create_user


class TestLoginUser:
    """Tests for login_user function."""

    async def test_login_user_success(self, db_session: AsyncSession):
        """Should login user and return tokens."""
        # Create user first
        await create_user(
            db_session,
            UserCreate(
                firstname="John",
                lastname="Doe",
                email="john@example.com",
                password="SecurePass123!",
                role_id=UserRoleEnum.USER,
            ),
        )

        token = await login_user(db_session, "john@example.com", "SecurePass123!")

        assert token.access_token is not None
        assert token.refresh_token is not None
        assert token.token_type == "bearer"

    async def test_login_user_wrong_password(self, db_session: AsyncSession):
        """Should raise HTTPException for wrong password."""
        await create_user(
            db_session,
            UserCreate(
                firstname="Jane",
                lastname="Smith",
                email="jane@example.com",
                password="CorrectPass123!",
                role_id=UserRoleEnum.USER,
            ),
        )

        with pytest.raises(HTTPException) as exc_info:
            await login_user(db_session, "jane@example.com", "WrongPass123!")

        assert exc_info.value.status_code == 401

    async def test_login_user_not_found(self, db_session: AsyncSession):
        """Should raise HTTPException for nonexistent email."""
        with pytest.raises(HTTPException) as exc_info:
            await login_user(db_session, "notexist@example.com", "Pass123!")

        assert exc_info.value.status_code == 401

    async def test_login_inactive_user(self, db_session: AsyncSession):
        """Should raise HTTPException for inactive user."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Bob",
                lastname="Jones",
                email="bob@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        # Mark user as inactive
        user.is_active = False
        db_session.add(user)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await login_user(db_session, "bob@example.com", "Pass123!")

        assert exc_info.value.status_code == 403


class TestRegisterUser:
    """Tests for register_user function."""

    async def test_register_user_success(self, db_session: AsyncSession):
        """Should register new user and return tokens."""
        from app.features.auth.schemas import RegisterRequest

        token = await register_user(
            db_session,
            RegisterRequest(
                firstname="Alice",
                lastname="Wonder",
                email="alice@example.com",
                password="SecurePass123!",
            ),
        )

        assert token.access_token is not None
        assert token.refresh_token is not None
        assert token.token_type == "bearer"

    async def test_register_user_duplicate_email(self, db_session: AsyncSession):
        """Should raise HTTPException for duplicate email."""
        from app.features.auth.schemas import RegisterRequest

        # Create first user
        await register_user(
            db_session,
            RegisterRequest(
                firstname="Carol",
                lastname="King",
                email="carol@example.com",
                password="Pass123!",
            ),
        )

        # Try to register with same email
        with pytest.raises(HTTPException) as exc_info:
            await register_user(
                db_session,
                RegisterRequest(
                    firstname="Carol2",
                    lastname="King2",
                    email="carol@example.com",
                    password="Pass456!",
                ),
            )

        assert exc_info.value.status_code == 400


class TestRefreshAccessToken:
    """Tests for refresh_access_token function."""

    async def test_refresh_access_token_success(self, db_session: AsyncSession):
        """Should generate new access token with valid refresh token."""
        # Create user and get refresh token
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Dave",
                lastname="Grohl",
                email="dave@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})

        token = await refresh_access_token(refresh_token)

        assert token.access_token is not None
        assert token.refresh_token is not None
        assert token.token_type == "bearer"

    async def test_refresh_access_token_invalid(self, db_session: AsyncSession):
        """Should raise HTTPException for invalid refresh token."""
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token("invalid-token")

        assert exc_info.value.status_code == 401

    async def test_refresh_access_token_wrong_type(self, db_session: AsyncSession):
        """Should raise HTTPException for access token instead of refresh token."""
        from datetime import timedelta

        from app.core.security import create_access_token

        user = await create_user(
            db_session,
            UserCreate(
                firstname="Eve",
                lastname="Evans",
                email="eve@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        # Create access token instead of refresh token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(minutes=30),
        )

        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(access_token)

        assert exc_info.value.status_code == 401


class TestRequestPasswordReset:
    """Tests for request_password_reset function."""

    async def test_request_password_reset_success(self, db_session: AsyncSession):
        """Should generate and return reset code."""
        await create_user(
            db_session,
            UserCreate(
                firstname="Frank",
                lastname="Sinatra",
                email="frank@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )

        reset_code = await request_password_reset(db_session, "frank@example.com")

        assert reset_code is not None
        assert len(reset_code) == 6
        assert reset_code.isdigit()

    async def test_request_password_reset_user_not_found(self, db_session: AsyncSession):
        """Should raise HTTPException for nonexistent user."""
        with pytest.raises(HTTPException) as exc_info:
            await request_password_reset(db_session, "notfound@example.com")

        assert exc_info.value.status_code == 404

    async def test_request_password_reset_inactive_user(self, db_session: AsyncSession):
        """Should raise HTTPException for inactive user."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Grace",
                lastname="Hopper",
                email="grace@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        user.is_active = False
        db_session.add(user)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await request_password_reset(db_session, "grace@example.com")

        assert exc_info.value.status_code == 403


class TestVerifyResetCode:
    """Tests for verify_reset_code function."""

    async def test_verify_reset_code_success(self, db_session: AsyncSession):
        """Should verify valid reset code."""
        await create_user(
            db_session,
            UserCreate(
                firstname="Henry",
                lastname="Ford",
                email="henry@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )

        reset_code = await request_password_reset(db_session, "henry@example.com")
        result = await verify_reset_code(db_session, "henry@example.com", reset_code)

        assert result is True

    async def test_verify_reset_code_invalid(self, db_session: AsyncSession):
        """Should raise HTTPException for invalid code."""
        await create_user(
            db_session,
            UserCreate(
                firstname="Iris",
                lastname="West",
                email="iris@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_reset_code(db_session, "iris@example.com", "000000")

        assert exc_info.value.status_code == 401

    async def test_verify_reset_code_user_not_found(self, db_session: AsyncSession):
        """Should raise HTTPException for nonexistent user."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_reset_code(db_session, "notfound@example.com", "123456")

        assert exc_info.value.status_code == 404


class TestConfirmPasswordReset:
    """Tests for confirm_password_reset function."""

    async def test_confirm_password_reset_success(self, db_session: AsyncSession):
        """Should reset password with valid code."""
        await create_user(
            db_session,
            UserCreate(
                firstname="Jack",
                lastname="Johnson",
                email="jack@example.com",
                password="OldPass123!",
                role_id=UserRoleEnum.USER,
            ),
        )

        reset_code = await request_password_reset(db_session, "jack@example.com")
        result = await confirm_password_reset(
            db_session, "jack@example.com", reset_code, "NewPass456!"
        )

        assert result is not None
        assert "success" in result.get("message", "").lower()

    async def test_confirm_password_reset_invalid_code(self, db_session: AsyncSession):
        """Should raise HTTPException for invalid code."""
        await create_user(
            db_session,
            UserCreate(
                firstname="Kate",
                lastname="Knight",
                email="kate@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )

        with pytest.raises(HTTPException) as exc_info:
            await confirm_password_reset(db_session, "kate@example.com", "000000", "NewPass456!")

        assert exc_info.value.status_code == 401

    async def test_confirm_password_reset_user_not_found(self, db_session: AsyncSession):
        """Should raise HTTPException for nonexistent user."""
        with pytest.raises(HTTPException) as exc_info:
            await confirm_password_reset(
                db_session, "notfound@example.com", "123456", "NewPass456!"
            )

        assert exc_info.value.status_code == 404
