from fastapi import APIRouter

from app.api.v1 import auth, events, health, registrations, sessions, speakers

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(sessions.router)
api_router.include_router(speakers.router)
api_router.include_router(registrations.router)
