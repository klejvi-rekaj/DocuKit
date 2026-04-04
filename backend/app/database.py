import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _build_connect_args() -> dict:
    if settings.database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
    connect_args=_build_connect_args(),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_database() -> None:
    from app.models import db_models  # noqa: F401

    os.makedirs("./data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
