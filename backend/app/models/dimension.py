from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Identity,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Dimension(Base):
    __tablename__ = "dimensions"

    dimension_id: Mapped[int] = mapped_column(
        SmallInteger,
        Identity(),
        primary_key=True,
    )
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    bengali_name: Mapped[str] = mapped_column(String(50))

    modules: Mapped[list["ModuleDimension"]] = relationship(  # noqa: F821
        back_populates="dimension",
        cascade="all, delete-orphan",
    )


class ModuleDimension(Base):
    __tablename__ = "module_dimensions"
    __table_args__ = (
        CheckConstraint(
            "display_order > 0",
            name="ck_module_dimensions_positive_display_order",
        ),
        UniqueConstraint(
            "module_id",
            "display_order",
            name="uq_module_dimensions_module_display_order",
        ),
    )

    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.module_id", ondelete="CASCADE"),
        primary_key=True,
    )
    dimension_id: Mapped[int] = mapped_column(
        ForeignKey("dimensions.dimension_id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_order: Mapped[int] = mapped_column(SmallInteger)

    module: Mapped["Module"] = relationship(back_populates="dimensions")  # noqa: F821
    dimension: Mapped["Dimension"] = relationship(back_populates="modules")  # noqa: F821
