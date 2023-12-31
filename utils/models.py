
from typing import List
from sqlalchemy import Table, Column, UniqueConstraint, ForeignKey, func
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    joinedload,
    Mapped,
    mapped_column
)
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.dialects.sqlite import (
    # BLOB,
    # BOOLEAN,
    # CHAR,
    # DATE,
    # DATETIME,
    # DECIMAL,
    FLOAT,
    INTEGER,
    # NUMERIC,
    # JSON,
    # SMALLINT,
    # TEXT,
    # TIME,
    TIMESTAMP,
    VARCHAR,
)


class Base(DeclarativeBase):
    """
    Base class for SQLAlchemy model classes.

    This class defines a common interface for model classes to convert instances to dictionaries and retrieve their keys.
    """
    pass

    def keys(self) -> list:
        """
        Returns keys of this object as a list.
        """
        return self.as_dict().keys()

    def as_dict(self):
        """
        Convert the SQLAlchemy model instance to a dictionary.

        Returns:
            dict: A dictionary representation of the model instance.
        """
        # Use introspection to retrieve all attributes of the model
        model_attributes = [attr for attr in dir(self) if not callable(getattr(self, attr)) and not attr.startswith("_")]

        # Create a dictionary by iterating through the attributes
        model_dict = {}
        for attr in model_attributes:
            try:
                value = getattr(self, attr)
                if isinstance(value, Base):
                    # If the attribute is another SQLAlchemy model instance, recursively call as_dict
                    model_dict[attr] = value.as_dict()
                else:
                    model_dict[attr] = value
            except DetachedInstanceError:
                model_dict[attr] = "instance not loaded."

        return model_dict


class Person(Base):
    __tablename__ = "persons"

    person_id: Mapped[int] = mapped_column(primary_key=True)
    fullname = Column(VARCHAR(32), nullable=False, unique=True)

    def __init__(self, fullname: str):
        self.fullname = fullname


class Country(Base):
    __tablename__ = "countries"

    country_id: Mapped[int] = mapped_column(primary_key=True)
    country_name = Column(VARCHAR(32), nullable=False, unique=True)

    def __init__(self, country_name: str):
        self.country_name = country_name


class Language(Base):
    __tablename__ = "languages"

    language_id: Mapped[int] = mapped_column(primary_key=True)
    language_name = Column(VARCHAR(32), nullable=False, unique=True)

    def __init__(self, language_name: str):
        self.language_name = language_name


class StorageLocation(Base):
    __tablename__ = "storage_locations"

    storage_id: Mapped[int] = mapped_column(primary_key=True)
    label = Column(VARCHAR(12), nullable=False, unique=True)
    paths = relationship("StoragePath", back_populates="storage")

    def __init__(self, label: str):
        self.label = label


class StoragePath(Base):
    __tablename__ = "storage_paths"

    path_id: Mapped[int] = mapped_column(primary_key=True)
    location_path = Column(VARCHAR(255), nullable=False, unique=True)
    storage_id: Mapped[int] = mapped_column(ForeignKey("storage_locations.storage_id"))
    storage = relationship("StorageLocation", back_populates="paths")
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.movie_id"))
    movie = relationship("Movie", back_populates="paths")

    def __init__(self, storage: StorageLocation, location_path: str):
        self.storage_id = storage.storage_id
        self.location_path = location_path


movie_genre_association = Table(
    "movies_movie_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.movie_id"), primary_key=True),
    Column("movie_genre_id", ForeignKey("movie_genres.movie_genre_id"), primary_key=True)
)


movie_actor_association = Table(
    "movie_actors",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.movie_id"), primary_key=True),
    Column("actor_id", ForeignKey("persons.person_id"), primary_key=True)
)


movie_director_association = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.movie_id"), primary_key=True),
    Column("director_id", ForeignKey("persons.person_id"), primary_key=True)
)


movie_country_association = Table(
    "movie_countries",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.movie_id"), primary_key=True),
    Column("country_id", ForeignKey("countries.country_id"), primary_key=True)
)


movie_language_association = Table(
    "movie_languages",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.movie_id"), primary_key=True),
    Column("language_id", ForeignKey("languages.language_id"), primary_key=True)
)


class MovieGenre(Base):

    __tablename__ = "movie_genres"

    movie_genre_id: Mapped[int] = mapped_column(primary_key=True)
    genre_name = Column(VARCHAR(32), nullable=False, unique=True)
    notion_id = Column(VARCHAR(36))

    def __init__(self, genre_name: str):
        self.genre_name = genre_name


class Movie(Base):
    __tablename__ = "movies"

    movie_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    notion_id = Column(VARCHAR(36))
    imdb_id = Column(VARCHAR(16))
    title = Column(VARCHAR(64), nullable=False)
    year = Column(INTEGER, nullable=True)
    poster_url = Column(VARCHAR(200))
    tagline_text = Column(VARCHAR(256))
    rating = Column(FLOAT)
    duration = Column(INTEGER)
    rank = Column(INTEGER)

    genres: Mapped[List[MovieGenre]] = relationship(secondary=movie_genre_association)
    countries: Mapped[List[Country]] = relationship(secondary=movie_country_association)
    languages: Mapped[List[Language]] = relationship(secondary=movie_language_association)
    directors: Mapped[List[Person]] = relationship(secondary=movie_director_association)
    actors: Mapped[List[Person]] = relationship(secondary=movie_actor_association)
    paths: Mapped[List[StoragePath]] = relationship(back_populates="movie")

    UniqueConstraint('title', 'year', sqlite_on_conflict='REPLACE')
    created = Column(TIMESTAMP, server_default=func.current_timestamp())
    last_update = Column(TIMESTAMP, onupdate=func.current_timestamp())

    def __init__(self, title: str, year: int):
        self.title = title
        self.year = year

    def __repr__(self):
        year = "" if self.year is None else f" ({self.year})"
        return f"{self.title}{year}"

    @property
    def unique_key(self):
        if self.year is None:
            return self.title
        else:
            return f"{self.year}-{self.title}"
