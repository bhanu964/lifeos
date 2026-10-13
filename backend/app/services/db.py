from contextlib import contextmanager
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.models.user import Base

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_DB_FILE = DATA_DIR / "lifeos_saas.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_FILE}"

_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Check environment variable DATABASE_URL if set
        import os
        db_url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        connect_args = {}
        if "sqlite" in db_url:
            connect_args["check_same_thread"] = False

        _engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        try:
            Base.metadata.create_all(bind=_engine)
        except Exception as e:
            logger.warning("Could not auto-create tables: %s", e)
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionFactory


def init_db():
    """Ensure database schema is created."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("LifeOS SaaS database initialized successfully.")


@contextmanager
def get_db_session():
    """Thread-safe context manager for database sessions."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
