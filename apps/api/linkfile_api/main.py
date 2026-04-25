from __future__ import annotations

from fastapi import FastAPI

from linkfile_api.api.router import api_router
from linkfile_api.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="LinkFile API", version="0.1.1", debug=settings.debug)
    app.include_router(api_router)
    return app


app = create_app()
