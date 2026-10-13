from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.lifespan import lifespan
from app.routers import auth, health, plays, predict, stats


def _cors_origins() -> list[str]:
    origins = {
        settings.frontend_url.rstrip("/"),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
    for raw in settings.cors_origins.split(","):
        origin = raw.strip().rstrip("/")
        if origin:
            origins.add(origin)
    return sorted(origins)


def create_app() -> FastAPI:
    app = FastAPI(title="Spotify Play History", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api = APIRouter(prefix="/api")
    api.include_router(health.router)
    api.include_router(auth.router)
    api.include_router(plays.router)
    api.include_router(predict.router)
    api.include_router(stats.router)
    app.include_router(api)
    return app
