from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_database_session
from app.models.dimension import Dimension, ModuleDimension
from app.models.language import Language
from app.models.module import Module
from app.schemas.catalog import DimensionPublic, LanguagePublic, ModulePublic


router = APIRouter(tags=["Catalog"])


@router.get("/languages", response_model=list[LanguagePublic])
async def list_languages(
    session: AsyncSession = Depends(get_database_session),
) -> list[LanguagePublic]:
    languages = await session.scalars(
        select(Language)
        .where(Language.is_active.is_(True))
        .order_by(Language.language_id)
    )
    return [LanguagePublic.model_validate(language) for language in languages]


@router.get("/modules", response_model=list[ModulePublic])
async def list_modules(
    session: AsyncSession = Depends(get_database_session),
) -> list[ModulePublic]:
    modules = list(
        await session.scalars(
            select(Module)
            .where(Module.is_active.is_(True))
            .order_by(Module.module_id)
        )
    )
    dimension_rows = await session.execute(
        select(
            ModuleDimension.module_id,
            Dimension.code,
            Dimension.name,
            Dimension.bengali_name,
            ModuleDimension.display_order,
        )
        .join(Dimension)
        .order_by(ModuleDimension.module_id, ModuleDimension.display_order)
    )
    dimensions_by_module: dict[int, list[DimensionPublic]] = {}
    for module_id, code, name, bengali_name, display_order in dimension_rows:
        dimensions_by_module.setdefault(module_id, []).append(
            DimensionPublic(
                code=code,
                name=name,
                bengali_name=bengali_name,
                display_order=display_order,
            )
        )

    return [
        ModulePublic(
            code=module.code,
            name=module.name,
            bengali_name=module.bengali_name,
            dimensions=dimensions_by_module.get(module.module_id, []),
        )
        for module in modules
    ]
