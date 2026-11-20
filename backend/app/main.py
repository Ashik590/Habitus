from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
