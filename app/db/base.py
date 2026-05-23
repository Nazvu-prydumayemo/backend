"""SQLAlchemy declarative base for all ORM models."""

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase, MappedAsDataclass):
    """Declarative base class for all SQLAlchemy ORM models in the application."""
