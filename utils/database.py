from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

# Create and configure the engine with a connection pool
engine = create_engine("sqlite:///media.sqlite", pool_pre_ping=True, pool_size=10, max_overflow=20)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Use a context manager for session creation
Session = sessionmaker(bind=engine)


def get_session() -> Session:
    """
    Returns a fresh database session
    """
    with Session() as session:
        return session


def create_tables() -> None:
    Base.metadata.create_all(engine)
