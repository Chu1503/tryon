from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.generation_jobs import GenerationManager
from app.services.storage import LocalStorage


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_storage(request: Request) -> LocalStorage:
    return request.app.state.storage


def get_generation_manager(request: Request) -> GenerationManager:
    return request.app.state.generation_manager
