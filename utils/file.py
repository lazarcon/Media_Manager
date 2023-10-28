import os
import json
import logging
import datetime

from typing import Dict, List, Callable

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

def missing_path_warning(label: str, path: str) -> None:
    """
    Log a warning message indicating that the path was not found and skipped.

    Args:
        label: The label of the path that was not found.
        path: The path that was not found.
    """
    logger.warning(f"{label} not found at {path}. Skipping.")


def process_locations(locations: List[Dict],
                      action_function: Callable[[str, str], None],
                      missing_function: Callable[[str, str], None] = missing_path_warning) -> None:
    """
    Process a list of media locations by applying a custom action function to each location.
    Locations that are not mounted or have missing paths are skipped.

    Args:
        locations: A list of dictionaries containing information about media locations.
                        Each dictionary should have 'label' and 'path' keys. A 'mount_point' is optional.
        action_function: A custom function to be applied to each location.
                        It should take 'label' and 'path' as arguments.
        missing_function: A custom function to be applied to each location that could not be found.
                        It should take 'label' and 'path' as arguments.

    Returns:
        None
    """
    for location in locations:
        path = location.get("path")
        label = location.get("label")
        mount_point = location.get("mount_point")

        if mount_point is None or os.path.ismount(mount_point):
            if os.path.exists(path):
                action_function(label, path)
            else:
                missing_function(label, path)
        else:
            logger.warning(f"Skipping drive {label} since it is not mounted.")


def get_file_age_in_days(file_path: str) -> float:
    """Calculates the age of a file in days.

    Args:
    file_path: The path to the file.

    Returns:
    The age of the file in days.
    """

    creation_time = os.path.getctime(file_path)
    creation_time_datetime = datetime.datetime.fromtimestamp(creation_time)
    current_time_datetime = datetime.datetime.today()
    time_difference = current_time_datetime - creation_time_datetime
    time_difference_in_seconds = time_difference.total_seconds()
    file_age_in_days = time_difference_in_seconds / 24
    return file_age_in_days
