"""Transfer the exercise catalog without exporting accounts or learner scores.

Run from backend: python -m app.catalog_transfer export catalog-export.json
Then: python -m app.catalog_transfer import catalog-export.json --env-file .env.production
"""
import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.models.exercise import Exercise
from app.models.language import Language


def catalog_exercise_title(data: dict, source_code: str, position: int, version: int) -> str:
    title = data.get("title")
    if title is None and version == 1:
        # Compatibility labels must not expose the original sentence to guests.
        prefix = {"bn": "অনুশীলন", "de": "Übung", "es": "Ejercicio"}.get(source_code, "Exercise")
        title = f"{prefix} #{position}"
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 30:
        raise ValueError(f"Exercise {position} needs a non-empty title of at most 30 characters.")
    return title.strip()


async def transfer(args: argparse.Namespace) -> None:
    settings = Settings(_env_file=args.env_file)
    engine = create_async_engine(settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            if args.operation == "export":
                languages = (await session.scalars(select(Language))).all()
                codes = {language.language_id: language.code for language in languages}
                exercises = (await session.scalars(select(Exercise))).all()
                payload = {
                    "version": 2,
                    "languages": [
                        {
                            "code": language.code,
                            "name": language.name,
                            "bengali_name": language.bengali_name,
                            "is_active": language.is_active,
                        }
                        for language in languages
                    ],
                    "exercises": [
                        {
                            "source_code": codes[exercise.source_language_id],
                            "target_code": codes[exercise.target_language_id],
                            "level": exercise.level,
                            "title": exercise.title,
                            "source_text": exercise.source_text,
                            "preferred_solutions": exercise.preferred_solutions,
                            "time_limit_seconds": exercise.time_limit_seconds,
                            "is_public": exercise.is_public,
                            "is_active": exercise.is_active,
                        }
                        for exercise in exercises
                    ],
                }
                # Exclusive creation prevents accidental replacement of an export.
                with Path(args.file).open("x", encoding="utf-8") as output:
                    json.dump(payload, output, ensure_ascii=False, indent=2)
                print(f"Exported {len(exercises)} exercises; no users or scores included.")
                return

            payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
            version = payload.get("version")
            if version not in (1, 2):
                raise ValueError("Unsupported catalog version.")
            if await session.scalar(select(func.count()).select_from(Exercise)):
                raise ValueError("Import requires an empty exercise table; no data was changed.")
            # Earlier migrations insert explicit language IDs. Synchronize identity
            # before inserting any additional languages from the local catalog.
            await session.execute(text(
                "SELECT setval(pg_get_serial_sequence('languages', 'language_id'), "
                "COALESCE((SELECT MAX(language_id) FROM languages), 1), "
                "EXISTS (SELECT 1 FROM languages))"
            ))
            existing = {
                language.code: language
                for language in (await session.scalars(select(Language))).all()
            }
            for data in payload["languages"]:
                if data["code"] not in existing:
                    language = Language(**data)
                    session.add(language)
                    existing[language.code] = language
            await session.flush()
            for position, data in enumerate(payload["exercises"], start=1):
                values = dict(data)
                source_code = values.pop("source_code")
                target_code = values.pop("target_code")
                values["title"] = catalog_exercise_title(data, source_code, position, version)
                # Older exports lack access flags; keep those exercises locked.
                values.setdefault("is_public", False)
                session.add(Exercise(
                    source_language_id=existing[source_code].language_id,
                    target_language_id=existing[target_code].language_id,
                    **values,
                ))
            await session.commit()
            print(f"Imported {len(payload['exercises'])} exercises.")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("export", "import"))
    parser.add_argument("file")
    parser.add_argument("--env-file", default=".env")
    asyncio.run(transfer(parser.parse_args()))


if __name__ == "__main__":
    main()
