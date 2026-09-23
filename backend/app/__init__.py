from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.lifespan import lifespan
from app.routers import auth, health, plays, predict, stats


def create_app() -> FastAPI:
    app = FastAPI(title="Spotify Play History", lifespan=lifespan)
    origins = {
        settings.frontend_url.rstrip("/"),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(plays.router)
    app.include_router(predict.router)
    app.include_router(stats.router)
    return app
