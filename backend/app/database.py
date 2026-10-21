"""Engine, sessao e Base do SQLAlchemy 2.0."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _normalize_db_url(url: str) -> str:
    """Garante o driver psycopg3. Hosts como Render/Neon/Heroku entregam a URL
    como 'postgres://' ou 'postgresql://' (sem o driver), o que faria o SQLAlchemy
    procurar o psycopg2 (ausente). Reescrevemos para 'postgresql+psycopg://'."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


_db_url = _normalize_db_url(settings.database_url)

# check_same_thread=False so somente para SQLite (dev/testes).
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

engine = create_engine(
    _db_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI: abre/fecha sessao por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
