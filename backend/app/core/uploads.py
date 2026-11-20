import logging
from pathlib import Path

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)

PROFILE_PICTURE_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "uploads" / "profile-pictures"
)
PROFILE_PICTURE_URL_PREFIX = "/media/profile-pictures"
MAX_PROFILE_PICTURE_SIZE_BYTES = 5 * 1024 * 1024


def _supabase_storage_url() -> str:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase storage credentials are not configured.")
    return (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/"
        f"{settings.supabase_storage_bucket}"
    )


async def store_profile_picture(filename: str, content: bytes, extension: str) -> str:
    if settings.profile_picture_storage == "supabase":
        content_type = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[extension]
        storage_url = _supabase_storage_url()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{storage_url}/{filename}",
                content=content,
                headers={
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                    "Content-Type": content_type,
                    "x-upsert": "false",
                },
            )
            response.raise_for_status()
        return (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/"
            f"{settings.supabase_storage_bucket}/{filename}"
        )

    PROFILE_PICTURE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    (PROFILE_PICTURE_DIRECTORY / filename).write_bytes(content)
    return f"{PROFILE_PICTURE_URL_PREFIX}/{filename}"


async def remove_stored_profile_picture(profile_picture_url: str | None) -> None:
    if not profile_picture_url:
        return
    if profile_picture_url.startswith(f"{PROFILE_PICTURE_URL_PREFIX}/"):
        delete_profile_picture(profile_picture_url)
        return
    if not settings.supabase_url:
        return
    prefix = (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/"
        f"{settings.supabase_storage_bucket}/"
    )
    if not profile_picture_url.startswith(prefix):
        return
    filename = profile_picture_url.removeprefix(prefix)
    if not filename or Path(filename).name != filename:
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.delete(
                f"{_supabase_storage_url()}/{filename}",
                headers={"Authorization": f"Bearer {settings.supabase_service_role_key}"},
            )
            response.raise_for_status()
    except (httpx.HTTPError, RuntimeError):
        logger.warning("Could not delete remote profile picture %s", filename)


def detect_profile_picture_extension(content: bytes) -> str | None:
    """Return a safe extension based on the file signature, not its filename."""
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if (
        len(content) >= 12
        and content[:4] == b"RIFF"
        and content[8:12] == b"WEBP"
    ):
        return "webp"
    return None


def delete_profile_picture(profile_picture_url: str | None) -> None:
    """Delete only files that belong to the managed profile-picture directory."""
    if not profile_picture_url:
        return

    expected_prefix = f"{PROFILE_PICTURE_URL_PREFIX}/"
    if not profile_picture_url.startswith(expected_prefix):
        return

    filename = profile_picture_url.removeprefix(expected_prefix)
    if not filename or Path(filename).name != filename:
        return

    try:
        (PROFILE_PICTURE_DIRECTORY / filename).unlink(missing_ok=True)
    except OSError:
        logger.warning(
            "Could not delete stored profile picture %s",
            filename,
            exc_info=True,
        )
