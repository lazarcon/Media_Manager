import os
import json
import logging

from typing import Dict

logger = logging.getLogger(__name__)

# Define constants for directory paths
UTILS_DIR = os.path.dirname(os.path.realpath(__file__))
APP_DIR = os.path.dirname(UTILS_DIR)
CONFIG_FILE = "config.json"


class FileNotFound(BaseException):
    """
    Exception raised if a file is not found at the given path.
    """
    def __init__(self, path: str) -> None:
        super().__init__(f"No file found at {path}")


class InvalidFileType(BaseException):
    """
    Exception raised if a file is not of the expected type.
    """
    def __init__(self, filename: str, filetype: str) -> None:
        super().__init__(
            f"File \"{filename}\" does not seem to be"
            + f" of type {filetype}")


def load_json(path_to_file: str = None) -> dict:
    """
    Load a JSON file and convert it to a dictionary.

    Args:
        path_to_file (str): Absolute or relative path to the JSON file.

    Returns:
        dict: Contents of the JSON file as a dictionary.

    Raises:
        FileNotFound: If the file does not exist at the given path.
        InvalidFileType: If the input file is not a valid JSON file.
    """
    logger.debug(f"Loading json file from: {path_to_file}")
    # Check if the file exists
    if not os.path.exists(path_to_file):
        raise FileNotFound(path_to_file)

    try:
        # Open the file and load the JSON data into a dictionary
        with open(path_to_file) as file:
            data = json.load(file)
    except BaseException as e:
        raise InvalidFileType(path_to_file, "json")
    logger.debug(f"File containing {len(list(data.items()))} items loaded successfully.")
    return data


def save_json(path_to_file: str = None, data: Dict = None) -> Dict:
    """
    Save data to a JSON file.

    Args:
        path_to_file (str): Absolute or relative path to the JSON file.
        data (dict): The data to save

    Returns:
        dict: Contents of the JSON file as a dictionary.
    """

    # Check if the file exists
    if os.path.exists(path_to_file):
        # and delete it, if it exists
        os.remove(path_to_file)

    # Convert dict to json
    json_object = json.dumps(data, indent=4)

    # Open the file and load the JSON data into a dictionary
    with open(path_to_file, "w") as file:
        file.write(json_object)

    return data


def load_config():
    """
    Loads the configuration from the config file.

    Returns:
        dict: A dictionary containing the configuration values.
    """
    path = os.path.join(APP_DIR, CONFIG_FILE)
    return load_json(path)
