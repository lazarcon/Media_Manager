import os
import logging
import requests

from pprint import pprint
from .file import load_json, save_json
from typing import List, Dict
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def get_movie_info(nfo_file_path):
    movie_info = {
        'genres': [],
        'actors': [],
        'directors': [],
        'countries': [],
    }

    try:
        tree = ET.parse(nfo_file_path)
        root = tree.getroot()

        # Extract genres
        for genre in root.findall(".//genre"):
            movie_info['genres'].append(genre.text)

        # Extract cast
        for actor in root.findall(".//actor"):
            name = actor.find('name').text
            # role = actor.find('role').text
            movie_info['actors'].append(f"{name}")
            if len(movie_info['actors']) >= 10:
                break

        # Extract directors
        for director in root.findall(".//director"):
            movie_info['directors'].append(director.text)

        # Extract directors
        for country in root.findall(".//country"):
            movie_info['countries'].append(country.text)

        movie_info['imdb_id'] = root.findall(".//id")[0].text
        movie_info['tagline'] = root.findall(".//tagline")[0].text
        movie_info['rating'] = float(root.findall(".//rating")[0].text)

    except Exception as e:
        print(f"Error parsing {nfo_file_path}: {str(e)}")

    return movie_info


def get_movie_poster_url(imdb_id, api_key):
    # Make a request to the OMDB API to get movie details
    omdb_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={api_key}"
    response = requests.get(omdb_url)
    data = response.json()

    # Check if the API returned a valid response
    if response.status_code == 200 and data.get('Poster'):
        return data['Poster']
    else:
        return ""


class InvalidRequest(BaseException):
    pass


class Notion:
    """
    A class for interacting with Notion.so databases to load and save records.
    """
    def __init__(self, api_key,
                 movie_database_id,
                 genre_database_id,
                 omdb_api_key):
        self.headers = {
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        self.movie_database_id = movie_database_id
        self.genre_database_id = genre_database_id
        self.omdb_api_key = omdb_api_key

    def load_records(self, database_id: str, num_pages: int = None) -> Dict:
        """
        Load records from a Notion database.

        Args:
            database_id (str): The ID of the Notion database.
            num_pages (int): The number of pages to retrieve (optional). If None, retrieve all pages.

        Returns:
            Dict: A dictionary containing loaded records.
        """
        filename = database_id + ".json"

        # Check if a cached version of the data exists and use it during debugging.
        if logger.getEffectiveLevel() == logging.DEBUG and os.path.exists(filename):
            return load_json(filename).get("data")
        else:
            url = f"https://api.notion.com/v1/databases/{database_id}/query"

            get_all = num_pages is None
            page_size = 100 if get_all else num_pages

            payload = {"page_size": page_size}
            response = requests.post(url, json=payload, headers=self.headers)

            # Check for errors in the response.
            if response.status_code != 200:
                message = f"Error requesting data from {url}. " \
                          f"Response-status: {response.status_code}. " \
                          f"Message: {response.content}"
                logger.error(message)
                raise InvalidRequest(url)

            data = response.json()

            results = data["results"]

            # Retrieve more pages if needed.
            while data["has_more"] and get_all:
                payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
                url = f"https://api.notion.com/v1/databases/{database_id}/query"
                response = requests.post(url, json=payload, headers=self.headers)
                data = response.json()
                results.extend(data["results"])

            # Cache the data during debugging.
            if logger.getEffectiveLevel() == logging.DEBUG:
                save_json(filename, {"data": results})
        return results

    def save_record(self, database_id: str, record: dict) -> None:
        """
        Save a record to a Notion database.

        Args:
            database_id (str): The ID of the Notion database.
            record (dict): A dictionary containing the record properties to be saved.

        Raises:
            InvalidRequest: If there's an error in the request.
        """
        url = "https://api.notion.com/v1/pages"
        payload = {"parent": {"database_id": database_id}, "properties": record}
        response = requests.post(url, headers=self.headers, json=payload)

        # Check for errors in the response.
        if response.status_code != 200:
            message = f"Error requesting data from {url}. " \
                      f"Response-status: {response.status_code}. " \
                      f"Message: {response.content}"
            logger.error(message)
            raise InvalidRequest(url)

    def query(self, database_id: str, filter) -> List[Dict]:
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        logger.debug(f"Executing query @ {url}")
        payload = {
            "filter": {
                "or": [
                    {
                        "property": list(filter.keys())[0],
                        "rich_text": {
                            "contains": list(filter.values())[0]
                        }
                    }
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
            raise InvalidRequest(url)

        data = response.json()
        logger.debug(f"data: {data}")
        return data["results"]

    def update_movie(self, root: str, dir: str):
        title, year = dir.rsplit('(', 1)
        title = title.strip()
        year = year.replace(')', '').strip()
        logger.debug(f"{year}: {title}")
        path_to_movie = os.path.join(root, dir)
        for filename in os.listdir(path_to_movie):
            logger.debug(filename)

        existing_movies = self.query(self.movie_database_id, {"Titel": title})
        if len(existing_movies) == 0:
            nfo_file_path = os.path.join(root, dir, title + ".nfo")
            if not os.path.exists(nfo_file_path):
                logger.warn(f"{nfo_file_path} not found for {title} ({year})")
            else:
                try:
                    movie_info = get_movie_info(nfo_file_path)
                except BaseException as e:
                    if movie_info is None:
                        logger.warn(f"Could not parse {nfo_file_path}")
                if "imdb_id" in list(movie_info.keys()):
                    movie_info["poster_url"] = get_movie_poster_url(movie_info['imdb_id'], self.omdb_api_key)
                pprint(movie_info)

    def load_records(self, database_id: str, num_pages: int = None) -> Dict:
        """
        Load records from a Notion database.

        Args:
            database_id (str): The ID of the Notion database.
            num_pages (int): The number of pages to retrieve (optional). If None, retrieve all pages.

        Returns:
            Dict: A dictionary containing loaded records.
        """
        filename = database_id + ".json"

        # Check if a cached version of the data exists and use it during debugging.
        if logger.getEffectiveLevel() == logging.DEBUG and os.path.exists(filename):
            return load_json(filename).get("data")
        else:
            url = f"https://api.notion.com/v1/databases/{database_id}/query"

            get_all = num_pages is None
            page_size = 100 if get_all else num_pages

            payload = {"page_size": page_size}
            response = requests.post(url, json=payload, headers=self.headers)

            # Check for errors in the response.
            if response.status_code != 200:
                message = f"Error requesting data from {url}. " \
                          f"Response-status: {response.status_code}. " \
                          f"Message: {response.content}"
                logger.error(message)
                raise InvalidRequest(url)

            data = response.json()

            results = data["results"]

            # Retrieve more pages if needed.
            while data["has_more"] and get_all:
                payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
                url = f"https://api.notion.com/v1/databases/{database_id}/query"
                response = requests.post(url, json=payload, headers=self.headers)
                data = response.json()
                results.extend(data["results"])

            # Cache the data during debugging.
            if logger.getEffectiveLevel() == logging.DEBUG:
                save_json(filename, {"data": results})
        return results

    def save_record(self, database_id: str, record: dict) -> None:
        """
        Save a record to a Notion database.

        Args:
            database_id (str): The ID of the Notion database.
            record (dict): A dictionary containing the record properties to be saved.

        Raises:
            InvalidRequest: If there's an error in the request.
        """
        url = "https://api.notion.com/v1/pages"
        payload = {"parent": {"database_id": database_id}, "properties": record}
        response = requests.post(url, headers=self.headers, json=payload)

        # Check for errors in the response.
        if response.status_code != 200:
            message = f"Error requesting data from {url}. " \
                      f"Response-status: {response.status_code}. " \
                      f"Message: {response.content}"
            logger.error(message)
            raise InvalidRequest(url)
