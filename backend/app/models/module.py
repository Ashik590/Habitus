from sqlalchemy import Boolean, Identity, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Module(Base):
    __tablename__ = "modules"

    module_id: Mapped[int] = mapped_column(
        SmallInteger,
        Identity(),
        primary_key=True,
    )
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    bengali_name: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )

    dimensions: Mapped[list["ModuleDimension"]] = relationship(  # noqa: F821
        back_populates="module",
        cascade="all, delete-orphan",
    )
