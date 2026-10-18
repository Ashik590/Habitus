from fastapi import APIRouter

from app.api.routes import auth, catalog, evaluations, exercises, health, users


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(evaluations.router)
api_router.include_router(exercises.router)
api_router.include_router(health.router)
api_router.include_router(users.router)
