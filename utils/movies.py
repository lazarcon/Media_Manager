import os
import logging
import requests
import mimetypes

from typing import List, Dict
from pprint import pprint

from .file import process_locations
from .notion import Notion
from .nfo import NFO
from .models import Movie, MovieGenre, Person, Country, Language, StoragePath, StorageLocation, func
from .database import get_session

logger = logging.getLogger(__name__)


class MoviePosterRepository:

    def __init__(self, omdb_api_key):
        self.omdb_api_key = omdb_api_key
        self.poster_cache = {}  # Cache to store poster URLs

    def fetch_movie_details(self, imdb_id: str):
        omdb_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={self.omdb_api_key}"

        try:
            response = requests.get(omdb_url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()

            if 'Poster' in data:
                return data['Poster']
            else:
                return None

        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching movie details for IMDb ID {imdb_id}: {e}")
            return None

    def get_movie_poster_url(self, imdb_id: str):
        # Return none if imdb_id is missing
        if imdb_id is None:
            return None
        # Check if the poster URL is cached
        elif imdb_id in self.poster_cache:
            return self.poster_cache[imdb_id]

        # Fetch movie details and cache the poster URL
        poster_url = self.fetch_movie_details(imdb_id)
        if poster_url:
            self.poster_cache[imdb_id] = poster_url

        return poster_url


class NotionMovie():

    def __init__(self):
        self.title = None
        self.notion_id = None
        self.imdb_id = None
        self.genres = []
        self.directors = []
        self.actors = []
        self.countries =  []
        self.locations = []
        self.languages = []
        self.year = None
        self.poster_url = None
        self.tagline = None
        self.rating = None
        self.duration = None
        self.path = None

    def in_notion(self) -> bool:
        """
        Checks, if the movie has a notion_id
        """
        return not self.notion_id is None

    @property
    def properties(self) -> dict:
        """
        Converts the Movie object to a dictionary
        """
        properties = {
            "Titel": {
                "id": "title",
                "type": "title",
                "title": [{
                        "type": "text",
                        "text": {"content": self.title}
                    }
                ]
            }
        }
        if self.year is not None:
            properties["Jahr"] = {"type": "number", "number": self.year}
        # Append countries if any
        if len(self.countries) > 0:
            properties["L\u00e4nder"] = {
                "type": "multi_select",
                "multi_select": [{"name": country} for country in self.countries]
            }

        # Append rating locations if any
        if self.rating is not None:
            properties["Rating"] = {
                "type": "select",
                "select": {
                    "name": "\u2605" * self.rating,
                }
            }

        # Append storage locations if any
        if len(self.locations) > 0:
            properties["Speicherorte"] = {
                "type": "multi_select",
                "multi_select": [{"name": location} for location in self.locations]
            }

        # Append tagline if any
        if self.tagline is not None:
            properties["Handlung"] = {
                "type": "rich_text",
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                        "content": self.tagline}
                    }
                ]
            }

        # Append imdb link if any
        if self.imdb_id is not None:
            properties["Imdb"] = {"type": "url", "url": f"https://www.imdb.com/title/{self.imdb_id}/"}

        # Append genres if any
        if len(self.genres) > 0:
            properties["Genre"] = {
                "type": "relation",
                "relation": [{"id": id} for id in self.genres]
            }

        # Append languages if any
        if len(self.languages) > 0:
            properties["Sprachen"] = {
                "type": "multi_select",
                "multi_select": [{"name": language} for language in self.languages]
            }

        # Append directors if any
        if len(self.directors) > 0:
            properties["Regie"] = {
                "type": "multi_select",
                "multi_select": [{"name": director} for director in self.directors]
            }

        # Append actors if any
        if len(self.actors) > 0:
            properties["Schauspieler"] = {
                "multi_select": [{"name": actor} for actor in self.actors]
            }

        # Append poster if any
        if self.poster_url is not None:
            properties["Poster"] = {
                "type": "files",
                "files": [
                    {
                        "name": self.title[:100],
                        "type": "external",
                        "external": {
                            "url": self.poster_url
                        }
                    }
                ]
            }
        if self.duration is not None:
            properties["Länge"] = {"type": "number", "number": self.duration}

        return properties

    def equals(self, movie_data: Dict) -> bool:
        """
        Checks if the records are equal
        """
        properties = movie_data["properties"]
        genres = properties["Genre"]["relation"]
        if len(genres) != len(self.genres):
            return False
        for genre in genres:
            if genre["id"] not in self.genres:
                return False

        taglines_rich_text = properties["Handlung"]["rich_text"]
        for tagline_rich_text in taglines_rich_text:
             if tagline_rich_text["text"]["content"] != self.tagline:
                 return False

        imdb_url = properties["Imdb"]["url"]
        if imdb_url != f"https://www.imdb.com/title/{self.imdb_id}/":
            return False

        countries = properties["Länder"]["multi_select"]
        if len(countries) != len(self.countries):
            return False
        for country in countries:
            if country["name"] not in self.countries:
                return False

        posters = properties["Poster"]["files"]
        for poster in posters:
            if poster["name"] != self.poster_url:
                return False

        rating = properties["Rating"]["select"]["name"]
        if self.rating and len(rating) != self.rating:
            return False

        directors = properties["Regie"]["multi_select"]
        if len(directors) != len(self.directors):
            return False
        for director in directors:
            if director["name"] not in self.directors:
                return False

        actors = properties["Schauspieler"]["multi_select"]
        if len(actors) != len(self.actors):
            return False
        for actor in actors:
            if actor["name"] not in self.actors:
                return False

        locations = properties["Speicherorte"]["multi_select"]
        previous_location_count = len(self.locations)
        for location in locations:
            if location["name"] not in self.locations:
                self.locations.append(location["name"])
        if len(locations) < previous_location_count:
            return False

        languages = properties["Sprachen"]["multi_select"]
        if len(languages) != len(self.languages):
            return False
        for language in languages:
            if language["name"] not in self.languages:
                return False

        return True


class RemoteMovieRepository(Notion):

    def __init__(self,
                 api_key: str,
                 movie_database_id: str,
                 genre_database_id: str):
        super().__init__(api_key)
        self.movie_database_id = movie_database_id
        self.genre_database_id = genre_database_id

        # self.load_genres()
        # self.movies = self.load_records(self.movie_database_id)

    def load_genres(self):
        genres = self.load_records(self.genre_database_id)
        self.genres = {}
        for genre in genres:
            for synonym in genre["properties"]["Synonyms"]["multi_select"]:
                self.genres[synonym["name"]] = genre["id"]

    def find_movie(self, title: str, year: int) -> List[Dict]:
        url = f"https://api.notion.com/v1/databases/{self.movie_database_id}/query"
        logger.debug(f"Executing query @ {url}")
        payload = {
            "filter": {
                "and": [
                    {
                        "property": "Titel",
                        "rich_text": {
                            "equals": title
                        }
                    },
                    {
                        "property": "Jahr",
                        "number": {
                            "equals": year
                        }
                    },
                ]
            }
        }
        response = requests.post(url, json=payload, headers=self.headers)
        # Check for errors in the response.
        if response.status_code != 200:
            message = f"Error requesting data from {url}. " \
                        f"Response-status: {response.status_code}. "
            logger.error(message)
            pprint(response.json()["message"])
            return None

        data = response.json()
        return data["results"]

    def add_movie(self, movie: NotionMovie):
        logger.debug(f"Adding {movie.title}")
        try:
            self.save_record(self.movie_database_id, movie.properties)
            print(f"Created movie record for: {movie.title}")
        except BaseException as e:
            logger.error(f"Error creating movie \"{movie.title}\":")
            logger.error(str(e))

    def update_movie(self, existing_movie: Dict, stored_movie: NotionMovie):
        if stored_movie.equals(existing_movie):
            print(f"Skipping \"{stored_movie.title}\" - unchanged")
            return

        logger.debug(f"Updating \"{stored_movie.title}\"")
        record_id = existing_movie["id"]
        # pprint(stored_movie.properties)
        self.update_record(self.movie_database_id, record_id, stored_movie.properties)
        print(f"Updated {stored_movie.title}")


class LocalMovieRepository:

    def __init__(self, session):
        self.session = session

    def _append_movie_path(self, movie: Movie, label: str, location_path: str):
        # Check if the path is already associated with the movie
        existing_path = self.session.query(StoragePath).filter(
            StoragePath.location_path == location_path,
            StoragePath.movie == movie
        ).first()

        if existing_path is not None:
            # The path is already associated with the movie
            return

        # If the path is not associated, create and add it to the movie
        storage = self.session.query(StorageLocation).filter(
            StorageLocation.label == label
        ).first()
        if storage is None:
            logger.debug(f"Creating storage {label}")
            storage = StorageLocation(label=label)
            self.session.add(storage)

        # Ensure the storage is persisted and has a valid storage_id
        self.session.flush()

        path = StoragePath(storage=storage, location_path=location_path)
        movie.paths.append(path)

    def _append_movie_genres(self, movie: Movie, genre_names: List[str]):
        if genre_names is None or len(genre_names) == 0:
            return
        # Query for existing genres and filter the list to avoid duplicates
        existing_genres = self.session.query(MovieGenre).filter(
            MovieGenre.genre_name.in_(genre_names)
        ).all()

        # Create new genres for those that don't already exist
        new_genres = [MovieGenre(genre_name=genre_name) for genre_name in genre_names if genre_name not in [g.genre_name for g in existing_genres]]
        self.session.add_all(new_genres)

        # Add both existing and new genres to the movie
        for genre in existing_genres + new_genres:
            movie.genres.append(genre)

    def _append_movie_actors(self, movie: Movie, actor_names: List[str]):
        # Query for existing actors and filter the list to avoid duplicates
        if actor_names is None or len(actor_names) == 0:
            return
        existing_actors = self.session.query(Person).filter(
            Person.fullname.in_(actor_names)
        ).all()

        # Create new actors for those that don't already exist
        new_actors = [Person(fullname=actor_name) for actor_name in actor_names if actor_name not in [a.fullname for a in existing_actors]]
        self.session.add_all(new_actors)

        # Add both existing and new genres to the movie
        for actor in existing_actors + new_actors:
            movie.actors.append(actor)

    def _append_movie_directors(self, movie: Movie, director_names: List[str]):
        if director_names is None or len(director_names) == 0:
            return
        # Query for existing directors and filter the list to avoid duplicates
        existing_directors = self.session.query(Person).filter(
            Person.fullname.in_(director_names)
        ).all()

        # Create new directors for those that don't already exist
        new_directors = [Person(fullname=director_name) for director_name in director_names if director_name not in [d.fullname for d in existing_directors]]
        self.session.add_all(new_directors)

        # Add both existing and new genres to the movie
        for director in existing_directors + new_directors:
            movie.directors.append(director)

    def _append_movie_countries(self, movie: Movie, country_names: List[str]):
        if country_names is None or len(country_names) == 0:
            return
        # Query for existing countries and filter the list to avoid duplicates
        existing_countries = self.session.query(Country).filter(
            Country.country_name.in_(country_names)
        ).all()

        # Create new countries for those that don't already exist
        new_countries = [Country(country_name=country_name) for country_name in country_names if country_name not in [c.country_name for c in existing_countries]]
        self.session.add_all(new_countries)

        # Add both existing and new genres to the movie
        for country in existing_countries + new_countries:
            movie.countries.append(country)

    def _append_movie_languages(self, movie: Movie, language_names: List[str]):
        if language_names is None or len(language_names) == 0:
            return
        # Query for existing languages and filter the list to avoid duplicates
        existing_languages = self.session.query(Language).filter(
            Language.language_name.in_(language_names)
        ).all()

        # Create new languages for those that don't already exist
        new_languages = [Language(language_name=language_name) for language_name in language_names if language_name not in [l.language_name for l in existing_languages]]
        self.session.add_all(new_languages)

        # Add both existing and new genres to the movie
        for language in existing_languages + new_languages:
            movie.countries.append(language)


    def find_movie_by_title_and_year(self, title: str, year: int) -> Movie:
        return self.session.query(Movie).filter(
            Movie.title == title,
            Movie.year == year
        ).first()

    def add_or_update_movie(self, nfo: NFO, label: str, movie_path: str):
        with self.session.begin() as transaction:
            movie = self.find_movie_by_title_and_year(title=nfo.title, year=nfo.year)
            if movie is None:
                logger.debug(f"Creating Movie from {nfo})")
                movie = Movie(title=nfo.title, year=nfo.year)
                self.session.add(movie)
            movie.duration = nfo.duration
            movie.rating = nfo.rating
            movie.imdb_id = nfo.imdb_id
            movie.tagline_text = nfo.tagline_text
            self._append_movie_path(movie, label, movie_path)
            self._append_movie_actors(movie, nfo.actors)
            self._append_movie_directors(movie, nfo.directors)
            self._append_movie_genres(movie, nfo.genres)
            self._append_movie_countries(movie, nfo.countries)
            self._append_movie_languages(movie, nfo.lanuages)

            transaction.commit()  # Commit the transaction

    def get_youngest_movie_creation(self):
        with self.session as session:
            youngest_creation = session.query(func.min(Movie.created)).scalar()
        return youngest_creation


class MovieManager(Notion):

    def __init__(self, api_key: str,
                movie_database_id: str,
                genre_database_id: str,
                omdb_api_key: str):
        self.remote_movies = RemoteMovieRepository(
            api_key=api_key,
            movie_database_id=movie_database_id,
            genre_database_id=genre_database_id)
        self.posters = MoviePosterRepository(omdb_api_key)

    def is_movie(self, filepath: str):
        """
        Check if a file is a video file based on its MIME type.

        :param filepath: The path to the file.
        :return: True if the file is a video, False otherwise.
        """
        mime_type, _ = mimetypes.guess_type(filepath)

        if mime_type:
            return mime_type.startswith('video')
        else:
            return False  # Handle cases where MIME type is not recognized

    def _remove_missing_movies(self):
        """
        Checks all movies stored in the database, to see if they are still
        present as stored.
        Skip unmounted drives, delete missing movies on unmounted drives
        """
        # TODO implement remove missing movies
        pass

    def _add_or_update_movie(self, label: str, movie_path: str, nfo_path):
        nfo_path = NFO.rename_nfo_file(nfo_path)
        try:
            nfo = NFO(nfo_path)
        except BaseException as e:
            logger.warn(f"Error parsing {nfo_path}: {str(e)}. Skipping.")
            return

        if not nfo.is_valid():
            _, movie_filename = os.path.split(movie_path)
            logger.warn(f"No title found for movie {movie_filename} in {nfo_path}. Skipping.")
            return

        # Add poster_url
        nfo.poster_url = self.posters.get_movie_poster_url(nfo.imdb_id)
        session = get_session()
        repository = LocalMovieRepository(session)
        repository.add_or_update_movie(nfo, label, movie_path)

    def _add_or_update_stored_movies(self, label: str, path: str) -> None:
        """
        Scan a directory for movie files and associated .nfo files and take actions based on the files found.

        :param label: A label or name for the location.
        :param path: The path to the directory to scan.
        """
        logger.debug(f"Updating movies stored @ {label} ({path})")
        for root, dirs, _ in os.walk(path, followlinks=True):
            for dir in dirs:
                if dir.startswith("."):
                    # Skip hidden directories
                    logger.debug(f"Skipping hidden directory {dir}")
                    continue
                folder = os.path.join(root, dir)
                nfo_files = []
                movies = []
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if self.is_movie(filename):
                        movies.append(filepath)
                    elif NFO.is_nfo_file(filepath):
                        nfo_files.append(filepath)
                if len(movies) == 1 and len(nfo_files) == 1:
                    movie_path = movies[0]
                    nfo_path = nfo_files[0]
                    self._add_or_update_movie(label, movie_path, nfo_path)
                elif len(movies) > 1:
                    logger.warn(f"More than one movie found in {folder}")
                elif len(nfo_files) > 1:
                    logger.warn(f"More than one .nfo file found in {folder}")
                elif len(nfo_files) == 1 and len(movies) == 0:
                    logger.warn(f"Found .nfo file but no movie in {folder}")
                elif len(nfo_files) == 0 and len(movies) == 1:
                    logger.warn(f"Found no .nfo file but a movie in {folder}")

    def _update_notion(self):
        """
        update the notion so database with new data from the local database
        """
        # TODO implement update of notion so
        pass


    def run(self, media_locations):
        """
        Updates the notion.so movie database

        First thing is, it should add stored movies on my local network to the notion.so database that are not already there.

        Second it should correct/change Metadata for movies in the notion.so database, that are stored on my local network.

        Third, for movies that are on notion.so, but not in my local network, remove locations that where searched, and leave films that have no storage location alone.

        """
        # locations = media_locations["movies"]
        locations = [{"label": "Wotan", "path": "/home/cola/Videos/Movies/Charlie Chaplin"}]
        self._remove_missing_movies()
        process_locations(locations, self._add_or_update_stored_movies)
        self._update_notion()
