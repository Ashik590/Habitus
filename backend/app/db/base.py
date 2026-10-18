from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class inherited by every SQLAlchemy database model."""


# Importing the models registers their tables in Base.metadata. Alembic uses
# this metadata when it generates database migrations.
from app import models  # noqa: E402, F401
