from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assets, garments, health, user
from app.config import get_settings
from app.database import create_database
from app.services.generation_jobs import GenerationManager, recover_interrupted_jobs
from app.services.storage import LocalStorage


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = LocalStorage(settings)
    storage.initialize()
    create_database()
    recover_interrupted_jobs(settings)
    app.state.storage = storage
    app.state.generation_manager = GenerationManager(settings, storage)
    yield
    app.state.generation_manager.shutdown()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.frontend_origin.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(user.router, prefix=settings.api_prefix)
app.include_router(garments.router, prefix=settings.api_prefix)
app.include_router(assets.router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "Digital Wardrobe API", "docs": "/docs"}
