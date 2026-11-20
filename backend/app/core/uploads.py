import logging
from pathlib import Path


logger = logging.getLogger(__name__)

PROFILE_PICTURE_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "uploads" / "profile-pictures"
)
PROFILE_PICTURE_URL_PREFIX = "/media/profile-pictures"
MAX_PROFILE_PICTURE_SIZE_BYTES = 5 * 1024 * 1024


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
