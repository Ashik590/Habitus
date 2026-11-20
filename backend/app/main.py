from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.uploads import PROFILE_PICTURE_DIRECTORY, PROFILE_PICTURE_URL_PREFIX


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend API for the AI-powered language practice application.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROFILE_PICTURE_DIRECTORY.mkdir(parents=True, exist_ok=True)
app.mount(
    PROFILE_PICTURE_URL_PREFIX,
    StaticFiles(directory=PROFILE_PICTURE_DIRECTORY),
    name="profile-pictures",
)

app.include_router(api_router, prefix=settings.api_v1_prefix)

# Register this last so API and media routes take precedence over SPA routing.
if settings.frontend_dist_dir:
    frontend_directory = Path(settings.frontend_dist_dir).resolve()
    app.mount(
        "/assets",
        StaticFiles(directory=frontend_directory / "assets"),
        name="frontend-assets",
    )

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith(("api/", "media/")):
            raise HTTPException(status_code=404, detail="Not found.")
        candidate = (frontend_directory / path).resolve()
        if not candidate.is_relative_to(frontend_directory):
            raise HTTPException(status_code=404, detail="Not found.")
        if candidate.is_file():
            return FileResponse(candidate)
        if Path(path).suffix:
            raise HTTPException(status_code=404, detail="Not found.")
        return FileResponse(frontend_directory / "index.html")
