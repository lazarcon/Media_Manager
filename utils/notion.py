import os
import logging
import requests

from pprint import pprint
from .file import load_json, save_json
from typing import List, Dict


logger = logging.getLogger(__name__)


class InvalidRequest(BaseException):
    pass


class Notion:
    """
    A class for interacting with Notion.so databases to load and save records.
    """
    def __init__(self, api_key):
        self.headers = {
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

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

    def save_record(self, database_id: str, properties: dict) -> None:
        """
        Save a record to a Notion database.

        Args:
            database_id (str): The ID of the Notion database.
            properties (dict): A dictionary containing the record properties to be saved.

        Raises:
            InvalidRequest: If there's an error in the request.
        """
        url = "https://api.notion.com/v1/pages"
        payload = {"parent": {"database_id": database_id}, "properties": properties}
        response = requests.post(url, headers=self.headers, json=payload)

        # Check for errors in the response.
        if response.status_code != 200:
            message = f"Error requesting data from {url}. " \
                      f"Response-status: {response.status_code}."
            logger.error(f"Request failed with status {response.status_code}")
            pprint(response.json()["message"])
            raise InvalidRequest(url)

    def update_record(self, database_id: str, record_id: str, properties: dict) -> None:
        """
        Save a record to a Notion database.

        Args:
            database_id (str): The ID of the Notion database.
            properties (dict): A dictionary containing the record properties to be saved.

        Raises:
            InvalidRequest: If there's an error in the request.
        """
        url = f"https://api.notion.com/v1/pages/{record_id}"
        payload = {"parent": {"database_id": database_id},
                   "properties": properties}
        response = requests.patch(url, headers=self.headers, json=payload)

        # Check for errors in the response.
        if response.status_code != 200:
            message = f"Error requesting data from {url}. " \
                      f"Response-status: {response.status_code}."
            logger.error(f"Request failed with status {response.status_code}")
            pprint(response.json()["message"])
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
        return data["results"]

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

