import os
import logging
import requests
import mimetypes
import datetime

from typing import List, Dict
from pprint import pprint

from .file import process_locations
from .nfo import NFO
from .database import get_session
from .models import (
    Movie,
    MovieGenre,
    Person,
    Country,
    Language,
    StoragePath,
    StorageLocation,
    func,
    joinedload)
from .notion import (
    NotionPage,
    NotionTitle,
    NotionNumber,
    NotionText,
    NotionSelect,
    NotionMultiSelect,
    NotionRelation,
    NotionURL,
    NotionExternalFile,
    Notion,
)

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


class NotionMovie(NotionPage):

    def __init__(self, data):
        super().__init__(data)
        properties = data.get("properties")
        # You can parse specific properties as needed
        self.title = NotionTitle("Titel", properties)
        self.year = NotionNumber("Jahr", properties)
        self.tagline = NotionText("Handlung", properties)
        self.rating = NotionSelect("Rating", properties)
        self.duration = NotionNumber("Dauer", properties)
        self.languages = NotionMultiSelect("Sprachen", properties)
        self.countries = NotionMultiSelect("L\u00e4nder", properties)
        self.locations = NotionMultiSelect("Speicherorte", properties)
        self.genres = NotionRelation("Genre", properties)
        self.imdb_url = NotionURL("Imdb", properties)
        self.poster_url = NotionExternalFile("Poster", properties)

    def __repr__(self):
        return f"{self.title.value} ({self.year.value})"

    def in_notion(self) -> bool:
        """
        Checks, if the movie has a notion_id
        """
        return self.id is not None

    @property
    def unique_key(self):
        if self.year is None:
            return self.title
        elif self.year.value is None:
            return self.title
        else:
            return f"{self.year.value}-{self.title.value}"

    def get_properties(self) -> dict:
        """
        Converts the Movie object to a dictionary
        """
        return {
            self.title.as_property(),
            self.year.as_property(),
            self.duration.as_property(),
            self.tagline.as_property(),
            self.rating.as_property(),
            self.countries.as_property(),
            self.languages.as_property(),
            self.genres.as_property(),
            self.imdb_url.as_property(),
            self.poster_url.as_property(),
            self.locations.as_property()
        }

    def update_from_movie(self, movie: Movie) -> None:
        """
        Updates Notion Movie with data from stored movie

        if len(self.genres.value) != len(self.genres):
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
        """


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

    def all_movies(self) -> List[NotionMovie]:
        records = self.load_records(self.movie_database_id)
        movies = []
        for record in records:
            try:
                movies.append(NotionMovie(record))
            except BaseException as e:
                logger.error(f"Could not create movie from: {record.get('url')}")
                logger.error(str(e))
                exit()
        return movies

    def remove_all_locations_from_movies(self, movie_ids: List[str]) -> None:
        logger.info("Removing locations from movies")
        payload = {
            "Speicherorte": {
                "type": "multi_select",
                "multi_select": []
            }
        }
        for movie_id in movie_ids:
            self.update_record(self.movie_database_id, movie_id, payload)

    def add_movie(self, movie: NotionMovie):
        logger.debug(f"Adding {movie.title}")
        try:
            self.add_record(self.movie_database_id, movie)
            print(f"Created movie record for: {movie.title}")
        except BaseException as e:
            logger.error(f"Error creating movie \"{movie.title}\":")
            logger.error(str(e))

    def update_movie(self, existing_movie: Dict, stored_movie: NotionMovie):
        if stored_movie.equals(existing_movie):
            print(f"Skipping \"{stored_movie.title}\" - unchanged")
            return

        logger.debug(f"Updating \"{stored_movie.title}\"")
        # pprint(stored_movie.properties)
        self.update_record(stored_movie.properties)
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
            movie.languages.append(language)

    def find_movie_by_title_and_year(self, title: str, year: int) -> Movie:
        return self.session.query(Movie).filter(
            Movie.title == title,
            Movie.year == year
        ).first()

    def add_or_update_movie(self, nfo: NFO,
                            label: str,
                            movie_path: str,
                            poster_repository: MoviePosterRepository):
        with self.session.begin() as transaction:
            movie = self.find_movie_by_title_and_year(title=nfo.title, year=nfo.year)
            if movie is None:
                logger.info(f"Creating new movie from {nfo})")
                movie = Movie(title=nfo.title, year=nfo.year)
                self.session.add(movie)
            if movie.duration is None:
                movie.duration = nfo.duration
            if movie.rating is None:
                movie.rating = nfo.rating
            if movie.imdb_id is None and nfo.imdb_id is not None:
                movie.imdb_id = nfo.imdb_id
            if movie.poster_url is None and movie.imdb_id is not None:
                movie.poster_url = poster_repository.get_movie_poster_url(movie.imdb_id)
            if movie.tagline_text is None or len(movie.tagline_text) == 0:
                movie.tagline_text = nfo.tagline_text
            self._append_movie_path(movie, label, movie_path)
            self._append_movie_actors(movie, nfo.actors)
            self._append_movie_directors(movie, nfo.directors)
            self._append_movie_genres(movie, nfo.genres)
            self._append_movie_countries(movie, nfo.countries)
            self._append_movie_languages(movie, nfo.languages)

            transaction.commit()  # Commit the transaction
        return movie

    def find_storage_paths_by_label(self, label: str) -> List[StoragePath]:
        with self.session as session:
            storage_paths = session.query(StoragePath) \
                .join(StorageLocation, StoragePath.storage_id == StorageLocation.storage_id) \
                .filter(StorageLocation.label == label) \
                .all()
        return storage_paths

    def delete_storage_paths(self, paths_to_delete: List[StoragePath]):
        with self.session.begin() as transaction:
            for path in paths_to_delete:
                self.session.delete(path)

            transaction.commit()

    def delete_movies_without_paths(self):
        deleted_movie_ids = []
        with self.session.begin() as transaction:
            # Find movies without associated storage paths
            movies_to_delete = self.session.query(Movie).filter(Movie.paths == None).all()
            # Loop through the movies to delete
            if len(movies_to_delete) > 0:
                logger.info(f"Deleting {len(movies_to_delete)} movies.")
            for movie in movies_to_delete:
                # Remove associations with directors, actors, countries, genres, and languages
                if movie.notion_id is not None:
                    deleted_movie_ids.append(movie.notion_id)
                movie.directors = []
                movie.actors = []
                movie.countries = []
                movie.genres = []
                movie.languages = []
                logger.debug(f"Deleting movie {movie}")
                self.session.delete(movie)
            transaction.commit()
        return deleted_movie_ids

    def get_last_movie_update(self):
        with self.session as session:
            last_update = session.query(func.max(Movie.last_update)).scalar()
        return last_update

    def all_movies(self):
        return (self.session.query(Movie)
                .options(
                    joinedload(Movie.languages),
                    joinedload(Movie.directors),
                    joinedload(Movie.actors),
                    joinedload(Movie.genres),
                    joinedload(Movie.countries),
                    joinedload(Movie.paths)
                )
                .all())


class MovieManager:

    def __init__(self, api_key: str,
                movie_database_id: str,
                genre_database_id: str,
                omdb_api_key: str):
        self.remote_movies = RemoteMovieRepository(
            api_key=api_key,
            movie_database_id=movie_database_id,
            genre_database_id=genre_database_id)
        self.posters = MoviePosterRepository(omdb_api_key)

    def _remove_missing_movies(self, locations: List[Dict]) -> List[str]:
        """
        Remove missing movies and their associations.

        This method checks all movies stored in the database to see if they are still
        present on mounted drives. It skips unmounted drives and deletes missing
        movies on unmounted drives.

        Args:
            locations (List[Dict]): List of dictionaries containing label and mount_point.

        Returns:
            List[str] notion_ids of deleted movies
        """
        session = get_session()
        repository = LocalMovieRepository(session)
        missing_paths = []

        for location in locations:
            label = location.get("label")
            mount_point = location.get("mount_point")

            if mount_point is not None and not os.path.ismount(mount_point):
                logger.warn(f"Skipping {label} because it is not mounted.")
                continue

            paths = repository.find_storage_paths_by_label(label=label)

            for path in paths:
                if not os.path.exists(path.location_path):
                    missing_paths.append(path.movie)

        if len(missing_paths) > 0:
            deleted_movie_ids = repository.delete_storage_paths(missing_paths)
            repository.delete_movies_without_paths()
            return deleted_movie_ids
        return []

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
        session = get_session()
        repository = LocalMovieRepository(session)
        repository.add_or_update_movie(nfo, label, movie_path, self.posters)

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

    def _compare_movies(self, local_movies: List[Movie], notion_movies: List[NotionMovie], last_update = None):
        """
        Compare local movie data with Notion movie data to identify changes.

        Args:
            local_movies (list): List of movie objects from your local database.
            notion_movies (list): List of movie objects from your Notion database.

        Returns:
            added_movies (list): Movies that are in local but not in Notion.
            updated_movies (list): Movies that exist in both local and Notion, but with differences.
            missing_movies (list): Movies that are in Notion but not in local.
        """
        added_movies = []
        updated_movies = []
        missing_movies = []

        # Create dictionaries for efficient lookups
        local_movie_dict = {f"{movie.unique_key})": movie for movie in local_movies}
        notion_movie_dict = {f"{movie.unique_key})": movie for movie in notion_movies}

        # Identify added and updated movies
        for title_year, local_movie in local_movie_dict.items():
            notion_movie = notion_movie_dict.get(title_year)
            if notion_movie is None:
                added_movies.append(local_movie)
            elif (
                last_update is None
                and local_movie.last_update is not None
                and local_movie.last_update > notion_movie.last_update
            ):
                updated_movies.append({"local_movie": local_movie, "notion_movie": notion_movie})
            elif (
                last_update is None
                and local_movie.last_update is not None
            ):
                updated_movies.append({"local_movie": local_movie, "notion_movie": notion_movie})
            elif (
                last_update is not None
                and last_update > notion_movie.last_update
            ):
                updated_movies.append({"local_movie": local_movie, "notion_movie": notion_movie})

        # Identify removed movies
        for title_year, notion_movie in notion_movie_dict.items():
            if title_year not in local_movie_dict:
                missing_movies.append(notion_movie)

        return added_movies, updated_movies, missing_movies

    def _update_notion(self, removed_movie_ids: List[str] = [], last_update = None):
        """
        update the notion so database with new data from the local database
        """
        self.remote_movies.remove_all_locations_from_movies(removed_movie_ids)
        session = get_session()
        local_movies = LocalMovieRepository(session).all_movies()
        notion_movies = self.remote_movies.all_movies()
        # Compare local data with Notion data
        added_movies, updated_movies, missing_movies = self._compare_movies(local_movies, notion_movies, last_update)

        # Update Notion records for added and updated movies
        print("Added movies:")
        for movie in added_movies:
            print("\t", movie)

        print("Updated movies:")
        for movie in updated_movies:
            print("\t", movie["notion_movie"])

        print("Missing movies:")
        for movie in missing_movies:
            print("\t", movie)

    def run(self, locations):
        """
        Updates the notion.so movie database

        First thing is, it should add stored movies on my local network to the notion.so database that are not already there.

        Second it should correct/change Metadata for movies in the notion.so database, that are stored on my local network.

        Third, for movies that are on notion.so, but not in my local network, remove locations that where searched, and leave films that have no storage location alone.

        """
        # locations = [{"label": "Wotan", "path": "/home/cola/Videos/Movies"}]

        # Get the last update before we are performing actions
        last_update = LocalMovieRepository(get_session()).get_last_movie_update()
        # last_update = datetime.strptime("2023-10-24 12:39:15", "%Y-%m-%d %H:%M:%S")
        if last_update is not None:
            logger.info(f"Last update: {last_update}")

        # Remove Missing Movies
        removed_movie_ids = self._remove_missing_movies(locations)
        # removed_movie_ids = []

        # Check for new movies or movie updates
        process_locations(locations, self._add_or_update_stored_movies)

        # Update the notion database
        # self._update_notion(removed_movie_ids, last_update)
