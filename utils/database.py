from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

engine = create_engine("sqlite:///media.sqlite")


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_session() -> Session:
    """
    Returns a fresh database session
    """
    session = sessionmaker(bind=engine)
    return session


def create_tables() -> None:
    Base.metadata.create_all(engine)
