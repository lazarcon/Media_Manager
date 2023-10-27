import os
import logging
import requests
import datetime

from abc import ABC, abstractmethod
from pprint import pprint
from .file import load_json, save_json
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


class InvalidRequest(BaseException):
    pass


class NotionProperty(ABC):

    def __init__(self, name: str, value: Dict):
        self.name = name
        self.value = value

    @abstractmethod
    def as_property(self) -> Dict:
        """
        Returns this property in notion format
        """
        pass


class NotionTitle(NotionProperty):

    def __init__(self, name: str, property: [Dict, str]):
        if isinstance(property, dict):
            try:
                value = property.get(name, {}).get("title", [{}])[0].get("text", {}).get("content")
            except BaseException:
                value = None
        else:
            value = property
        super().__init__(name, value)

    def as_property(self) -> Dict:
        return {
                self.name: {
                    "id": "title",
                    "type": "title",
                    "title": [{
                            "type": "text",
                            "text": {"content": self.value}
                        }
                    ]
                }
            }


class NotionNumber(NotionProperty):

    def __init__(self, name: str, property: [Dict, int, float]):
        if isinstance(property, dict):
            try:
                value = property.get(name, {}).get("number")
            except BaseException:
                value = None
        else:
            value = property
        super().__init__(name, value)

    def as_property(self) -> Dict:
        if self.value is not None:
            return {self.name: {"type": "number", "number": self.value}}


class NotionText(NotionProperty):

    def __init__(self, name: str, property: [Dict, str]):
        if isinstance(property, dict):
            try:
                value = property.get(name, {}).get("rich_text", [{}])[0].get("text", {}).get("content")
            except BaseException:
                value = None
        else:
            value = property
        super().__init__(name, value)

    def as_property(self) -> Dict:
        if self.value is not None:
            return {
                self.name: {
                    "type": "rich_text",
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                            "content": self.value}
                        }
                    ]
                }
            }


class NotionSelect(NotionProperty):

    def __init__(self, name: str, property: [Dict, str]):
        if isinstance(property, dict):
            try:
                value = property.get(name, {"select": {}}).get("select", {"name": None}).get("name")
            except BaseException:
                value = None
        else:
            value = property
        super().__init__(name, value)

    def as_property(self) -> Dict:
        if self.value is not None:
            return {
                self.name: {
                    "type": "select",
                    "select": {
                        "name": self.value,
                    }
                }
            }


class NotionMultiSelect(NotionProperty):

    def __init__(self, name: str, property: [Dict, List[str]]):
        if isinstance(property, dict):
            try:
                value = [element["name"] for element in property.get(name, {}).get("multi_select", [])]
            except BaseException:
                value = None
        else:
            value = property
        super().__init__(name, value)

    def as_property(self) -> Dict:
        if self.value is not None:
            return {
                self.name: {
                    "type": "multi_select",
                    "multi_select": [{"name": value} for value in self.value]
                }
            }


class NotionRelation(NotionProperty):

    def __init__(self, name: str, property: [Dict, List[str]]):
        if isinstance(property, dict):
            try:
                value = [element["name"] for element in property.get(name, {}).get("relation", [])]
            except BaseException:
                value = None
        else:
            value = property
        super().__init__(name, value)

    def as_property(self) -> Dict:
        if self.value is not None:
            return {
                self.name: {
                    "type": "relation",
                    "relation": [{"id": id} for id in self.value]
                }
            }


class NotionURL(NotionProperty):

    def __init__(self, name: str, property: [Dict, str]):
        if isinstance(property, dict):
            try:
                value = property.get(name, {}).get("url")
            except BaseException:
                value = None
        else:
            value = property
        super().__init__(name, value)

    def as_property(self) -> Dict:
        if self.value is not None:
            return {
                self.name: {"type": "url", "url": self.value}
            }


class NotionExternalFile(NotionProperty):

    def __init__(self, name: str, property: [Dict, str]):
        if isinstance(property, dict):
            try:
                value = property.get(name, {}).get("files", [{}])[0].get("external", {}).get("url")
            except BaseException:
                value = None
        else:
            value = property
        super().__init__(name, value)

    def as_property(self) -> Dict:
        if self.value is not None:
            return {
                self.name: {
                    "type": "files",
                    "files": [
                        {
                            "name": self.value[:100],
                            "type": "external",
                            "external": {
                                "url": self.value
                            }
                        }
                    ]
                }
            }


class NotionPage(ABC):

    def __init__(self, data):
        if isinstance(data, dict):
            self.id = data.get("id")
            self.created_time = data.get("created_time")
            self.last_edited_time = data.get("last_edited_time")
            self.created_by = data.get("created_by")
            self.last_edited_by = data.get("last_edited_by")
            self.cover = data.get("cover")
            self.icon = data.get("icon")
            self.parent = data.get("parent")
            self.archived = data.get("archived")
            self.url = data.get("url")
            self._properties = data.get("properties")

    @property
    def last_update(self):
        date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        return datetime.datetime.strptime(self.last_edited_time, date_format)

    @abstractmethod
    def get_properties(self):
        return self._properties


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

    def load_records(self, database_id: str, num_pages: int = None) -> List[Dict]:
        """
        Load records from a Notion database.

        Args:
            database_id (str): The ID of the Notion database.
            num_pages (int): The number of pages to retrieve (optional). If None, retrieve all pages.

        Returns:
            List[Dict]: An array containing dictionaries of the loaded records.
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

    def add_record(self, database_id: str, page: NotionPage) -> str:
        """
        Save a record to a Notion database.

        Args:
            database_id (str): The ID of the Notion database.
            properties (dict): A dictionary containing the record properties to be saved.


        Returns:
            id of newly created record
        Raises:
            InvalidRequest: If there's an error in the request.
        """
        url = "https://api.notion.com/v1/pages"
        payload = {"parent": {"database_id": database_id}, "properties": page.get_properties()}
        response = requests.post(url, headers=self.headers, json=payload)

        # Check for errors in the response.
        if response.status_code == 200:
            return response.json()["id"]
        else:
            message = f"Error requesting data from {url}. " \
                      f"Response-status: {response.status_code}."
            logger.error(f"Request failed with status {response.status_code}")
            pprint(response.json()["message"])
            raise InvalidRequest(url)

    def update_record(self, page: NotionPage) -> None:
        """
        Save a record to a Notion database.

        Args:
            page (NotionPage): the original, but updated page.

        Raises:
            InvalidRequest: If there's an error in the request.
        """
        url = f"https://api.notion.com/v1/pages/{page.id}"
        payload = {"parent": page.parent,
                   "properties": page.get_properties()}
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

