from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.utils.logging import setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(title="Sources API", version="1.0.0")
    app.include_router(router)
    return app


app = create_app()
