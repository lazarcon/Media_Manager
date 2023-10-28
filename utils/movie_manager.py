import os
import logging
import requests
import mimetypes
import datetime
import shutil

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
from .imdb import ImdbRepository

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
        if isinstance(data, dict):
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
            self.rank = NotionNumber("Rang", properties)
        elif isinstance(data, Movie):
            self.id = data.notion_id
            self.title = NotionTitle("Titel", data.title)
            self.year = NotionNumber("Jahr", data.year)
            self.tagline = NotionText("Handlung", data.tagline_text)
            if data.rating is not None and data.rating > 0:
                stars = "\u2605" * int(round(data.rating)/ 2)
                if stars != "":
                    self.rating = NotionSelect("Rating", stars)
            else:
                self.rating = None
            self.duration = NotionNumber("Dauer", data.duration)
            self.languages = NotionMultiSelect("Sprachen", [language.language_name for language in data.languages])
            self.countries = NotionMultiSelect("L\u00e4nder", [country.country_name for country in data.countries])
            self.locations = NotionMultiSelect("Speicherorte", [path.storage.label for path in data.paths])
            self.genres = NotionRelation("Genre", [genre.notion_id for genre in data.genres if genre.notion_id is not None])
            self.imdb_url = NotionURL("Imdb", f"https://www.imdb.com/title/{data.imdb_id}/")
            self.poster_url = NotionExternalFile("Poster", data.poster_url)
            self.rank = NotionNumber("Rang", data.rank)

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
            return self.title.value
        elif self.year.value is None:
            return self.title.value
        else:
            return f"{self.year.value}-{self.title.value}"

    def get_properties(self) -> dict:
        """
        Converts the Movie object to a dictionary
        """
        properties = {}
        properties |= self.title.as_property()
        if self.year.value is not None:
            properties |= self.year.as_property()
        if self.duration.value is not None:
            properties |= self.duration.as_property()
        if self.tagline.value is not None:
            properties |= self.tagline.as_property()
        if self.rating is not None and self.rating.value is not None:
            properties |= self.rating.as_property()
        if self.imdb_url.value is not None:
            properties |= self.imdb_url.as_property()
        if self.poster_url.value is not None:
            properties |= self.poster_url.as_property()
        if self.rank.value is not None:
            properties |= self.rank.as_property()
        if self.genres.value is not None and len(self.genres.value) > 0:
            properties |= self.genres.as_property()
        if self.countries.value is not None and len(self.countries.value) > 0:
            properties |= self.countries.as_property()
        if self.languages.value is not None and len(self.languages.value) > 0:
            properties |= self.languages.as_property()
        if self.locations.value is not None and len(self.locations.value) is not None:
            properties |= self.locations.as_property()

        return properties


class NotionMovieRepository(Notion):

    def __init__(self,
                 api_key: str,
                 movie_database_id: str):
        super().__init__(api_key)
        self.movie_database_id = movie_database_id

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
        logger.info("Removing locations from Notion movies")
        payload = {
            "Speicherorte": {
                "type": "multi_select",
                "multi_select": []
            }
        }
        for movie_id in movie_ids:
            self.execute_update(self.movie_database_id, movie_id, payload)

    def update_movie_locations(self, movie_id: str, locations: list[str]) -> None:
        logger.info("Adding locations for Notion movies")
        payload = {
            "Speicherorte": {
                "type": "multi_select",
                "multi_select":[{"name": value} for value in locations]
            }
        }
        self.execute_update(self.movie_database_id, movie_id, payload)

    def add_movie(self, movie: NotionMovie):
        try:
            return self.add_record(self.movie_database_id, movie)
        except BaseException as e:
            logger.error(f"Error creating movie \"{movie}\":")
            logger.error(str(e))


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
        logger.debug(f"Searching for all storage paths of {label}")
        with self.session as session:
            storage_paths = session.query(StoragePath) \
                .join(StorageLocation, StoragePath.storage_id == StorageLocation.storage_id) \
                .filter(StorageLocation.label == label) \
                .all()
        logger.debug(f"Found {len(storage_paths)} movies for {label}")
        return storage_paths

    def delete_storage_paths(self, paths_to_delete: List[StoragePath]):
        logger.info("Deleting storage paths")
        with self.session.begin() as transaction:
            for path in paths_to_delete:
                logger.debug(f"Deleting {path.location_path}")
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

    def get_last_movie_update(self) -> datetime.datetime:
        with self.session as session:
            last_update = session.query(func.max(Movie.last_update)).scalar()
        return last_update


class MovieUpdater:
    def __init__(self, session, notion_repository):
        self.session = session
        self.notion_repository = notion_repository
        self.logger = logging.getLogger(__class__.__name__)

    def compare_movies(self, local_movies: List[Movie], notion_movies: List[NotionMovie]):
        """
        Compare local movie data with Notion movie data to identify changes.

        Args:
            local_movies (list): List of movie objects from your local database.
            notion_movies (list): List of movie objects from your Notion database.

        Returns:
            added_movies (list): Movies that are in local but not in Notion.
            overlapping_movies (list): Movies that exist in both local and Notion.
            missing_movies (list): Movies that are in Notion but not in local.
        """
        added_movies = []
        overlapping_movies = []
        missing_movies = []

        # Create dictionaries for efficient lookups
        local_movie_dict = {f"{movie.unique_key}": movie for movie in local_movies}
        notion_movie_dict = {f"{movie.unique_key}": movie for movie in notion_movies}
        # Identify added and updated movies
        for unique_key, local_movie in local_movie_dict.items():
            notion_movie = notion_movie_dict.get(unique_key)
            if notion_movie is None:
                added_movies.append(local_movie)
            else:
                overlapping_movies.append({"local_movie": local_movie, "notion_movie": notion_movie})

        # Identify removed movies
        for title_year, notion_movie in notion_movie_dict.items():
            if title_year not in local_movie_dict:
                missing_movies.append(notion_movie)
        return added_movies, overlapping_movies, missing_movies

    def _all_movies(self) -> List[Movie]:
        """Retrieve all movies from the local database."""
        return (self.session.query(Movie)
                .options(
                    joinedload(Movie.languages),
                    joinedload(Movie.directors),
                    joinedload(Movie.actors),
                    joinedload(Movie.genres),
                    joinedload(Movie.countries),
                    joinedload(Movie.paths).joinedload(StoragePath.storage),
                )
                .all())

    def update(self, notion_movies: List[NotionMovie]) -> List[NotionMovie]:
        """
        Compare local movies with Notion movies, add new movies to Notion, and update existing ones.

        Args:
            notion_movies (list): List of movie objects from your Notion database.
            notion_repository (RemoteMovieRepository): The repository for interacting with Notion.
            last_update (datetime.datetime, optional): A datetime filter for last updates. Defaults to None.

        Returns:
            list: Movies missing in Notion.
        """
        with self.session.begin() as transaction:
            local_movies = self._all_movies()
            added_movies, overlapping_movies, missing_movies = self.compare_movies(local_movies, notion_movies)
            self.logger.info(f"Adding {len(added_movies)} movies to Notion:")
            changes = 0
            for local_movie in added_movies:
                notion_movie = NotionMovie(local_movie)
                # Try to add the movie to Notion
                try:
                    # notion_id = self.notion_repository.add_movie(notion_movie)
                    # local_movie.notion_id = notion_id
                    self.logger.info(f"Added {notion_movie}")
                    changes += 1
                except Exception as e:
                    self.logger.error(f"Failed to add {notion_movie}: {e}")
            print(f"Added {changes} ")

            changes = 0
            self.logger.info(f"Updating {len(overlapping_movies)} movies in Notion, if needed:")
            for record in overlapping_movies:
                local_movie = record.get("local_movie")
                notion_movie = record.get("notion_movie")
                # Check if notion_id is set.
                if local_movie.notion_id is None:
                    local_movie.notion_id = notion_movie.id
                    self.logger.debug(f"Setting missing notion id for {local_movie}.")
                elif local_movie.notion_id != notion_movie.id:
                    local_movie.notion_id = notion_movie.id
                    self.logger.debug(f"Changing notion id for {local_movie}.")

                had_changes = False
                local_locations = [path.storage.label for path in local_movie.paths]
                for local_location in local_locations:
                    if local_location not in notion_movie.locations.value:
                        had_changes = True
                        notion_movie.locations.value.append(local_location)
                if local_movie.tagline_text != notion_movie.tagline.value:
                    had_changes = True
                    notion_movie.tagline.value = local_movie.tagline_text
                if (local_movie.imdb_id is not None
                    and (notion_movie.imdb_url is None
                         or notion_movie.imdb_url.value != f"https://www.imdb.com/title/{local_movie.imdb_id}/")
                    ):
                    had_changes = True
                    notion_movie.imdb_url.value = f"https://www.imdb.com/title/{local_movie.imdb_id}/"
                if local_movie.rating is not None and local_movie.rating != 0.0:
                    rating = "\u2605" * int(round(local_movie.rating/ 2))
                    if rating == "" and notion_movie.rating is not None:
                        notion_movie.rating = None
                        had_changes = True
                    elif notion_movie.rating is None and rating != "":
                        notion_movie.rating = NotionSelect("Rating", rating)
                        had_changes = True
                    elif notion_movie.rating.value is None or notion_movie.rating.value != rating:
                        had_changes = True
                        notion_movie.rating.value = rating
                if local_movie.rank is None:
                    if notion_movie.rank.value is not None:
                        notion_movie.rank.value = None
                        had_changes = True
                else:
                    if (notion_movie.rank.value is None
                        or notion_movie.rank.value != local_movie.rank
                    ):
                        notion_movie.rank.value = local_movie.rank
                        had_changes = True

                # Add more compares as necessary
                if had_changes:
                    # Try to update the record in Notion
                    try:
                        self.notion_repository.update_record(notion_movie)
                        print(f"Updated {notion_movie} ({notion_movie.id})")
                        self.logger.info(f"Updated {notion_movie} ({notion_movie.id})")
                        changes += 1
                    except Exception as e:
                        self.logger.error(f"Failed to update {notion_movie}: {e}")
            print(f"Updated {changes} movies.")
            transaction.commit()
        return missing_movies

    def update_imdb_movie_rankings(self):
        imdb = ImdbRepository()
        if imdb.is_update_due():
            logger.info("Updating IMDB Movie rankings")
            rankings = imdb.get_rankings()
            with self.session.begin() as transaction:
                for imdb_id, top_movie in rankings.items():
                    movies = self.session.query(Movie).filter(Movie.imdb_id == imdb_id).all()
                    for movie in movies:
                        if movie.rank is None or movie.rank != top_movie.get("rank"):
                            logger.debug(f"Adjusting rank of {movie} to {top_movie.get('rank')}")
                            previous_ranked_movie = self.session.query(Movie).filter(Movie.rank == top_movie.get('rank'))
                            if previous_ranked_movie:
                                previous_ranked_movie.rank = None
                            movie.rank = top_movie.get("rank")
                transaction.commit()
        else:
            logger.info("Skipping update of IMDB Top 250 rankings")

    def get_backup_movies(self):
        return (self.session.query(Movie)
            .options(
                joinedload(Movie.paths).joinedload(StoragePath.storage),
            )
            # .limit(1)
            .all())

    def notion_only(self):
        with self.session.begin() as transaction:
            # backup_location = self.session.query(StorageLocation).filter(StorageLocation.label == "Backup").first()
            local_movies = self.get_backup_movies()
            movie = local_movies[0]
            print(f"Simulating {movie}")
            locations = [path.storage.label for path in movie.paths]
            if "Backup" not in locations:
                locations.append("Backup")
                self.notion_repository.update_movie_locations(movie.notion_id, locations)

    def backup(self, backup_folder: str):
        with self.session.begin() as transaction:
            try:
                backup_location = self.session.query(StorageLocation).filter(StorageLocation.label == "Backup").first()
                if not backup_location:
                    backup_location = StorageLocation("Backup")
                    self.session.add(backup_location)

                local_movies = self.get_backup_movies()

                for movie in local_movies:
                    locations = [path.storage.label for path in movie.paths]
                    if "Backup" not in locations and ("Wotan" in locations or "fritzNAS" in locations):
                        source_movie_path = movie.paths[0].location_path
                        source_folder, movie_file = os.path.split(source_movie_path)
                        first_letter = movie.title[0]
                        target_folder = os.path.join(backup_folder, first_letter, str(movie))
                        print(f"Copying file {source_folder} to {target_folder}")
                        shutil.copytree(source_folder, target_folder)
                        target_folder = target_folder.replace("share/Multimedia/", "")
                        target_movie_file = os.path.join(target_folder, movie_file)
                        copied_movie_path = StoragePath(backup_location, target_movie_file)
                        movie.paths.append(copied_movie_path)
                        locations.append("Backup")

                        if movie.notion_id is not None:
                            self.notion_repository.update_movie_locations(movie.notion_id, locations)

                        logger.info(f"Created backup for {movie}")
                transaction.commit()
            except (shutil.Error, FileNotFoundError) as e:
                logger.error(f"Error copying file: {e}")
                # transaction.rollback()

class MovieManager:
    def __init__(self, api_key: str, movie_database_id: str, omdb_api_key: str):
        self.notion_repository = NotionMovieRepository(
            api_key=api_key,
            movie_database_id=movie_database_id
        )
        self.poster_repository = MoviePosterRepository(omdb_api_key)

    def remove_missing_movies(self, locations: List[Dict]) -> List[str]:
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
        logger.debug("Removing missing movies")
        session = get_session()
        repository = LocalMovieRepository(session)
        missing_paths = []

        for location in locations:
            label = location.get("label")
            mount_point = location.get("mount_point")
            if mount_point is not None and not os.path.ismount(mount_point):
                logger.warning(f"Skipping {label} because it is not mounted.")
                continue

            paths = repository.find_storage_paths_by_label(label=label)

            for path in paths:
                if not os.path.exists(path.location_path):
                    logger.debug(f"Found missing location: {path.location_path}")
                    missing_paths.append(path)

        if not missing_paths:
            logger.debug("No missing movie paths found.")
            return []

        repository.delete_storage_paths(missing_paths)
        deleted_movie_ids = repository.delete_movies_without_paths()
        return deleted_movie_ids

    def is_movie_file(self, filename: str) -> bool:
        """
        Check if a file is a video file based on its MIME type.

        :param filename: The name of the file.
        :return: True if the file is a video, False otherwise.
        """
        mime_type, _ = mimetypes.guess_type(filename)

        if mime_type:
            return mime_type.startswith('video')
        return False

    def add_or_update_movie(self, label: str, movie_path: str, nfo_path):
        """
        Add or update a movie based on the provided label, movie_path, and NFO file path.

        Args:
            label (str): A label or name for the location.
            movie_path (str): The path to the movie file.
            nfo_path (str): The path to the NFO file associated with the movie.

        This function adds the movie to the local database or updates its information if it already exists.

        If the NFO file is not valid or lacks essential information, the function logs a warning and skips the movie.

        """
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
        repository.add_or_update_movie(nfo, label, movie_path, self.poster_repository)

    def add_or_update_stored_movies(self, label: str, path: str) -> None:
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
                    if self.is_movie_file(filename):
                        movies.append(filepath)
                    elif NFO.is_nfo_file(filepath):
                        nfo_files.append(filepath)
                if len(movies) == 1 and len(nfo_files) == 1:
                    movie_path = movies[0]
                    nfo_path = nfo_files[0]
                    self.add_or_update_movie(label, movie_path, nfo_path)
                elif len(movies) > 1:
                    logger.warning(f"More than one movie found in {folder}")
                elif len(nfo_files) > 1:
                    logger.warning(f"More than one .nfo file found in {folder}")
                elif len(nfo_files) == 1 and len(movies) == 0:
                    logger.warning(f"Found .nfo file but no movie in {folder}")
                elif len(nfo_files) == 0 and len(movies) == 1:
                    logger.warning(f"Found no .nfo file but a movie in {folder}")

    def update_imdb_rankings(self):
        session = get_session()
        movie_updater = MovieUpdater(session, self.notion_repository)
        movie_updater.update_imdb_movie_rankings()

    def update_notion(self, removed_movie_ids: List[str] = []):
        """
        Update the Notion database with new data from the local database.
        """
        self.notion_repository.remove_all_locations_from_movies(removed_movie_ids)
        session = get_session()
        notion_movies = self.notion_repository.all_movies()
        movie_updater = MovieUpdater(session, self.notion_repository)
        wishlist = movie_updater.update(notion_movies)
        print(f"Wishlist {len(wishlist)} movies:")
        for movie in wishlist:
            print(f"\t{movie}")

    def backup(self, backup_location: Dict):
        # mount_point = backup_location.get("mount_point")
        """
        TODO Activate, when ready
        if mount_point and not os.path.ismount(mount_point):
            logger.error(f"Backup failed. {mount_point} not mounted.")
            return
        """
        session = get_session()
        updater = MovieUpdater(session, self.notion_repository)
        updater.backup(backup_folder=backup_location.get("path"))
        # updater.notion_only()

    def run(self, locations):
        """
        Execute the movie management process.

        Args:
            locations (List[Dict]): List of dictionaries containing label and mount_point for movie locations.

        This function performs the following steps:
        1. Removes missing movies that are no longer found on mounted drives.
        2. Checks for new movies or movie updates in specified locations.
        3. Updates the Notion database with new data from the local database.

        """
        # Remove Missing Movies
        removed_movie_ids = self.remove_missing_movies(locations)

        # Check for new movies or movie updates
        process_locations(locations, self.add_or_update_stored_movies)

        # Update imdb rankings
        self.update_imdb_rankings()

        # Update the Notion database
        self.update_notion(removed_movie_ids)
