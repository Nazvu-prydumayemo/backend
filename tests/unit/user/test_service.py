"""Unit tests for user service layer."""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.user.schemas import UserCreate, UserRoleEnum
from app.features.user.service import (
    change_user_password,
    create_user,
    delete_user_by_id,
    export_user_data,
    get_user_by_email,
    get_user_by_id,
    get_users,
    normalize_email,
    update_user_profile,
)


class TestNormalizeEmail:
    """Tests for normalize_email utility."""

    def test_lowercase_conversion(self):
        """Email should be converted to lowercase."""
        assert normalize_email("TEST@EXAMPLE.COM") == "test@example.com"

    def test_whitespace_stripping(self):
        """Leading/trailing whitespace should be removed."""
        assert normalize_email("  test@example.com  ") == "test@example.com"

    def test_combined(self):
        """Whitespace and case should both be normalized."""
        assert normalize_email("  TEST@EXAMPLE.COM  ") == "test@example.com"


class TestGetUsers:
    """Tests for get_users function."""

    async def test_get_users_empty(self, db_session: AsyncSession):
        """Should return empty sequence when no users exist."""
        users = await get_users(db_session)
        assert len(users) == 0

    async def test_get_users_multiple(self, db_session: AsyncSession):
        """Should retrieve all users."""
        # Create test users
        for i in range(3):
            await create_user(
                db_session,
                UserCreate(
                    firstname=f"User{i}",
                    lastname=f"Last{i}",
                    email=f"user{i}@example.com",
                    password="Pass123!",
                    role_id=UserRoleEnum.USER,
                ),
            )

        users = await get_users(db_session)
        assert len(users) >= 3


class TestGetUserById:
    """Tests for get_user_by_id function."""

    async def test_get_user_by_id_success(self, db_session: AsyncSession):
        """Should retrieve user by ID."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="John",
                lastname="Doe",
                email="john@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        found = await get_user_by_id(db_session, user.id)
        assert found is not None
        assert found.id == user.id
        assert found.email == "john@example.com"

    async def test_get_user_by_id_not_found(self, db_session: AsyncSession):
        """Should return None for nonexistent user."""
        result = await get_user_by_id(db_session, 99999)
        assert result is None


class TestGetUserByEmail:
    """Tests for get_user_by_email function."""

    async def test_get_user_by_email_success(self, db_session: AsyncSession):
        """Should retrieve user by email."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Jane",
                lastname="Smith",
                email="jane@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        found = await get_user_by_email(db_session, "jane@example.com")
        assert found is not None
        assert found.id == user.id

    async def test_get_user_by_email_case_insensitive(self, db_session: AsyncSession):
        """Email lookup should be case-insensitive."""
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

        found = await get_user_by_email(db_session, "BOB@EXAMPLE.COM")
        assert found is not None
        assert found.id == user.id

    async def test_get_user_by_email_not_found(self, db_session: AsyncSession):
        """Should return None for nonexistent email."""
        result = await get_user_by_email(db_session, "notreal@example.com")
        assert result is None


class TestCreateUser:
    """Tests for create_user function."""

    async def test_create_user_success(self, db_session: AsyncSession):
        """Should create a new user with hashed password."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Alice",
                lastname="Wonder",
                email="alice@example.com",
                password="SecurePass123!",
                role_id=UserRoleEnum.USER,
            ),
        )

        assert user is not None
        assert user.email == "alice@example.com"
        assert user.firstname == "Alice"
        # Password should be hashed, not plaintext
        assert user.password != "SecurePass123!"

    async def test_create_user_duplicate_email(self, db_session: AsyncSession):
        """Should raise HTTPException for duplicate email."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="First",
                lastname="User",
                email="duplicate@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        with pytest.raises(HTTPException) as exc_info:
            await create_user(
                db_session,
                UserCreate(
                    firstname="Second",
                    lastname="User",
                    email="duplicate@example.com",
                    password="Pass456!",
                    role_id=UserRoleEnum.USER,
                ),
            )

        assert exc_info.value.status_code == 400
        assert "already registered" in exc_info.value.detail.lower()

    async def test_create_user_email_normalized(self, db_session: AsyncSession):
        """Email should be normalized on creation."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Carol",
                lastname="King",
                email="CAROL@EXAMPLE.COM",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        assert user.email == "carol@example.com"


class TestDeleteUserById:
    """Tests for delete_user_by_id function."""

    async def test_delete_user_success(self, db_session: AsyncSession):
        """Should delete an existing user."""
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

        deleted = await delete_user_by_id(db_session, user.id)
        assert deleted is not None
        assert deleted.id == user.id

        # Verify user is actually deleted
        found = await get_user_by_id(db_session, user.id)
        assert found is None

    async def test_delete_user_not_found(self, db_session: AsyncSession):
        """Should return None when deleting nonexistent user."""
        result = await delete_user_by_id(db_session, 99999)
        assert result is None


class TestExportUserData:
    """Tests for export_user_data function."""

    async def test_export_user_data_success(self, db_session: AsyncSession):
        """Should export all user data."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Eve",
                lastname="Anderson",
                email="eve@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        data = await export_user_data(db_session, user.id)

        assert data is not None
        assert "profile" in data
        assert "orders" in data
        assert data["profile"].id == user.id

    async def test_export_user_data_not_found(self, db_session: AsyncSession):
        """Should raise HTTPException for nonexistent user."""
        with pytest.raises(HTTPException) as exc_info:
            await export_user_data(db_session, 99999)

        assert exc_info.value.status_code == 404


class TestUpdateUserProfile:
    """Tests for update_user_profile function."""

    async def test_update_user_profile_firstname(self, db_session: AsyncSession):
        """Should update user's firstname."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Frank",
                lastname="Sinatra",
                email="frank@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        updated = await update_user_profile(db_session, user, firstname="Francis")

        assert updated.firstname == "Francis"
        assert updated.lastname == "Sinatra"

    async def test_update_user_profile_lastname(self, db_session: AsyncSession):
        """Should update user's lastname."""
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

        updated = await update_user_profile(db_session, user, lastname="Murray")

        assert updated.firstname == "Grace"
        assert updated.lastname == "Murray"

    async def test_update_user_profile_both(self, db_session: AsyncSession):
        """Should update both firstname and lastname."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Henry",
                lastname="Ford",
                email="henry@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        updated = await update_user_profile(db_session, user, firstname="Henry", lastname="Wells")

        assert updated.firstname == "Henry"
        assert updated.lastname == "Wells"

    async def test_update_user_profile_no_changes(self, db_session: AsyncSession):
        """Should handle no updates gracefully."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Iris",
                lastname="West",
                email="iris@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        updated = await update_user_profile(db_session, user)

        assert updated.firstname == "Iris"
        assert updated.lastname == "West"


class TestChangeUserPassword:
    """Tests for change_user_password function."""

    async def test_change_user_password_success(self, db_session: AsyncSession):
        """Should change user's password."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Jack",
                lastname="Johnson",
                email="jack@example.com",
                password="OldPass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        # Store original password hash before update
        original_password = user.password

        updated = await change_user_password(db_session, user, "OldPass123!", "NewPass456!")

        assert updated.password != original_password
        # New password should be hashed
        assert updated.password != "NewPass456!"

    async def test_change_user_password_wrong_current(self, db_session: AsyncSession):
        """Should raise HTTPException if current password is incorrect."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Kate",
                lastname="Knight",
                email="kate@example.com",
                password="CorrectPass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        with pytest.raises(HTTPException) as exc_info:
            await change_user_password(db_session, user, "WrongPass123!", "NewPass456!")

        assert exc_info.value.status_code == 401

    async def test_change_user_password_same_as_old(self, db_session: AsyncSession):
        """Should raise HTTPException if new password same as current."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Liam",
                lastname="Lewis",
                email="liam@example.com",
                password="SamePass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        with pytest.raises(HTTPException) as exc_info:
            await change_user_password(db_session, user, "SamePass123!", "SamePass123!")

        assert exc_info.value.status_code == 400
        assert "cannot be the same" in exc_info.value.detail.lower()
