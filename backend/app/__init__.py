from fastapi import FastAPI

from app.lifespan import lifespan
from app.routers import auth, plays, predict


def create_app() -> FastAPI:
    app = FastAPI(title="Spotify Play History", lifespan=lifespan)
    app.include_router(auth.router)
    app.include_router(plays.router)
    app.include_router(predict.router)
    return app
