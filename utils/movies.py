import os
import logging
import requests

import xml.etree.ElementTree as ET

from typing import List, Dict
from pprint import pprint

from .notion import Notion

logger = logging.getLogger(__name__)


class Movie:
    title: str = None
    original_title: str = None
    notion_id: str = None
    imdb_id: str = None
    genres: List[str] = []
    directors: List[str] = []
    actors: List[str] = []
    countries: List[str] = []
    locations: List[str] = []
    languages: List[str] = []
    year: int = None
    poster_url: str = None
    tagline: str = None
    rating: int = None

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
                        "name": self.poster_url,
                        "type": "external",
                        "external": {
                            "url": self.poster_url
                        }
                    }
                ]
            }
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


class MovieManager(Notion):

    def __init__(self, api_key,
                movie_database_id,
                genre_database_id,
                omdb_api_key):
        super().__init__(api_key)
        self.movie_database_id = movie_database_id
        self.genre_database_id = genre_database_id
        self.omdb_api_key = omdb_api_key
        self.load_genres()
        self.movies = self.load_records(self.movie_database_id)

    def load_genres(self):
        genres = self.load_records(self.genre_database_id)
        self.genres = {}
        for genre in genres:
            for synonym in genre["properties"]["Synonyms"]["multi_select"]:
                self.genres[synonym["name"]] = genre["id"]

    def get_movie_poster_url(self, imdb_id):
        # Make a request to the OMDB API to get movie details
        omdb_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={self.omdb_api_key}"
        response = requests.get(omdb_url)
        data = response.json()

        # Check if the API returned a valid response
        if response.status_code == 200 and data.get('Poster'):
            return data["Poster"]
        return None

    def to_movie(self, label: str, nfo_file_path: str) -> Movie:
        movie = Movie()
        tree = ET.parse(nfo_file_path)
        root = tree.getroot()
        movie.title = root.find(".//title").text
        movie.original_title = root.find(".//originaltitle").text
        movie.year = int(root.find(".//year").text)
        movie.tagline = root.find(".//tagline").text

        # Extract imdb id
        movie.imdb_id = root.find(".//id").text
        if movie.imdb_id is not None:
            movie.poster_url = self.get_movie_poster_url(movie.imdb_id)

        # Extract rating
        rating = root.find(".//rating").text
        if rating is not None:
            try:
                stars = int(round(float(rating) / 2, 0))
                movie.rating = stars
            except BaseException:
                # rating could not be converted, so just ignore this
                pass

        # Extract genres
        for genre in root.findall(".//genre"):
            movie.genres.append(self.genres[genre.text])

        # Extract cast
        for actor in root.findall(".//actor"):
            name = actor.find('name').text
            # role = actor.find('role').text
            movie.actors.append(name)
            # Not more than the top three named actors
            if len(movie.actors) >= 3:
                break

        # Extract directors
        for director in root.findall(".//director"):
            movie.directors.append(director.text)

        # Extract countries
        for country in root.findall(".//country"):
            movie.countries.append(country.text)

        # Extract languages
        for audio_element in root.findall(".//fileinfo/streamdetails/audio"):
            language_element = audio_element.find("language")
            if language_element is not None:
                movie.languages.append(language_element.text)

        movie.locations.append(label)
        return movie

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

    def add_movie(self, movie: Movie):
        logger.debug(f"Adding {movie.title}")
        try:
            pprint(movie.properties)
            # self.save_record(self.movie_database_id, movie.properties)
        except BaseException as e:
            logger.error(str(e))

    def update_movie(self, existing_movie: Dict, stored_movie: Movie):
        pprint(stored_movie.properties)
        if stored_movie.equals(existing_movie):
            logger.debug(f"\"{stored_movie.title}\" is unchanged")
            return

        logger.debug(f"Updating \"{stored_movie.title}\"")
        record_id = existing_movie["id"]

        # self.update_record(self.movie_database_id, record_id, stored_movie.properties)

    def add_or_update_movie(self, label: str, root: str, dir: str):
        title, year = dir.rsplit('(', 1)
        title = title.strip()
        year = int(year.replace(')', '').strip())
        existing_movies = self.find_movie(title, year)
        nfo_file_path = os.path.join(root, dir, title + ".nfo")
        if not os.path.exists(nfo_file_path):
            logger.warn(f"{nfo_file_path} not found for {title} ({year})")
        else:
            try:
                movie = self.to_movie(label, nfo_file_path)
            except BaseException as e:
                logger.warn(f"Could not create movie from {nfo_file_path}. Skipping")
                logger.warn(f"Reason: {str(e)}")
                return

            if len(existing_movies) == 0:
                self.add_movie(movie)
            elif len(existing_movies) == 1:
                self.update_movie(existing_movies[0], movie)
            else:
                logger.warn(f"Multiple matching movies found for {title} ({year}). Skipping")

    def add_or_update_stored_movies(self, label: str, path: str) -> None:
        logger.debug(f"Updating movies stored @ {label} ({path})")
        counter = 0
        for root, dirs, filenames in os.walk(path, followlinks=True):
            for dir in dirs:
                if "(" in dir and ")" in dir:
                    # If there are brackets we have a valid movie
                    self.add_or_update_movie(label, root, dir)
                    counter += 1
                    if counter >= 2:
                        exit()

    def add_or_update_movies(self, media_locations):
        self.do_with_all_locations(media_locations, self.add_or_update_stored_movies)

    def update(self, media_locations):
        """
        Updates the notion.so movie database

        First thing is, it should add stored movies on my local network to the notion.so database that are not already there.

        Second it should correct/change Metadata for movies in the notion.so database, that are stored on my local network.

        Third, for movies that are on notion.so, but not in my local network, remove locations that where searched, and leave films that have no storage location alone.

        """
        self.add_or_update_movies(media_locations["movies"])
