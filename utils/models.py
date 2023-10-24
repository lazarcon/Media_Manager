
from typing import List
from sqlalchemy import Table, Column, UniqueConstraint, ForeignKey, func
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    synonym,
    Mapped,
    mapped_column
)
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.dialects.sqlite import (
    BLOB,
    BOOLEAN,
    CHAR,
    DATE,
    DATETIME,
    DECIMAL,
    FLOAT,
    INTEGER,
    NUMERIC,
    JSON,
    SMALLINT,
    TEXT,
    TIME,
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
    name = Column(VARCHAR(32), nullable=False, unique=True)


class Country(Base):

    __tablename__ = "countries"

    country_id: Mapped[int] = mapped_column(primary_key=True)
    name = Column(VARCHAR(32), nullable=False, unique=True)


class Language(Base):

    __tablename__ = "languages"

    language_id: Mapped[int] = mapped_column(primary_key=True)
    name = Column(VARCHAR(32), nullable=False, unique=True)


class Path(Base):

    __tablename__ = "paths"

    path_id: Mapped[int] = mapped_column(primary_key=True)
    path = Column(VARCHAR(255), nullable=False, unique=True)
    storage_id: Mapped[int] = mapped_column(ForeignKey("storages.storage_id"))
    storage = relationship("Storage", back_populates="paths")
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.movie_id"))
    movie = relationship("Movie", back_populates="paths")


class Storage(Base):

    __tablename__ = "storages"

    storage_id: Mapped[int] = mapped_column(primary_key=True)
    name = Column(VARCHAR(12), nullable=False, unique=True)
    paths = relationship("Path", back_populates="storage")


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
    name = Column(VARCHAR(32), nullable=False, unique=True)
    notion_id = Column(VARCHAR(36))


class Movie(Base):

    __tablename__ = "movies"

    movie_id: Mapped[int] = mapped_column(primary_key=True)
    notion_id = Column(VARCHAR(36))
    imdb_id = Column(VARCHAR(16))
    title = Column(VARCHAR(64), nullable=False)
    year = Column(INTEGER, nullable=False)
    poster_url = Column(VARCHAR(200))
    tagline = Column(VARCHAR(256))
    rating = Column(VARCHAR(5))
    length = Column(INTEGER)
    genres: Mapped[List[MovieGenre]] = relationship(secondary=movie_genre_association)
    countries: Mapped[List[Country]] = relationship(secondary=movie_country_association)
    languages: Mapped[List[Country]] = relationship(secondary=movie_language_association)
    directors: Mapped[List[Person]] = relationship(secondary=movie_director_association)
    actors: Mapped[List[Person]] = relationship(secondary=movie_actor_association)
    paths: Mapped[List[Path]] = relationship(back_populates="movie")
    UniqueConstraint('title', 'year', sqlite_on_conflict='REPLACE')
    created = Column(TIMESTAMP, default=func.current_timestamp())

