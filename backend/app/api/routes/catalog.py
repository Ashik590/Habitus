from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_database_session
from app.models.language import Language
from app.schemas.catalog import LanguagePublic


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
