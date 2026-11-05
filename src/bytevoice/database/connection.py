"""Database connection and session factory for ByteVoice.

Supports both SQLite (for zero-setup local development and tests)
and PostgreSQL (for production and Docker).
"""

from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure data directory exists for SQLite
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Default to SQLite file in data/ if DATABASE_URL is not set
DEFAULT_SQLITE_URL = f"sqlite:///{DATA_DIR / 'bytevoice.db'}"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)
if not DATABASE_URL:
    DATABASE_URL = DEFAULT_SQLITE_URL

# Normalize PostgreSQL driver for SQLAlchemy 2.0 (psycopg2)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# SQLite needs check_same_thread=False for FastAPI multithreaded workers
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields an independent database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

