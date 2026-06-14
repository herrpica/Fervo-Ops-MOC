"""Database engine and session for the OMOC app (SQLite via SQLAlchemy)."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite file lives next to the backend package. For Azure, swap DATABASE_URL for
# Azure SQL / PostgreSQL via the env var — no model changes required.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = "sqlite:///" + os.path.join(BASE_DIR, "omoc.db")
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
