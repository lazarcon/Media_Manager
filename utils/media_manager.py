import os
import logging

from pprint import pprint

from .notion import Notion

logger = logging.getLogger(__name__)


class MediaManager:

    def __init__(self, config):
        self.notion = Notion(
            api_key = config["notion_api_key"],
            movie_database_id=config["notion_media"]["movies"]["movie_db"],
            genre_database_id=config["notion_media"]["movies"]["genre_db"],
            omdb_api_key=config["omdb_api_key"]
        )
        self.local_media_locations = config["local_media"]

    def update_movie_storage(self, label: str, path: str) -> None:
        logger.debug(f"Updating movies stored @ {label} ({path})")
        counter = 0
        for root, dirs, filenames in os.walk(path, followlinks=True):
            for dir in dirs:
                if "(" in dir and ")" in dir:
                    # If there are brackets we have a valid movie
                    self.notion.update_movie(root, dir)
                    counter += 1
                if counter >= 1:
                    exit()

    def update_movies(self) -> None:
        logger.debug("Updating Movies")
        # Read all local directories and update Notion.so
        for storage in self.local_media_locations["movies"]:
            try:
                self.update_movie_storage(label=storage["label"], path=storage["path"])
            except BaseException as e:
                logger.warn(f"Could not update movies from {storage['label']} @ {storage['path']}")
                logger.error(str(e))
        logger.debug("Done updating Movies")

    def update(self) -> None:
        # Go through all local storage locations and update database items
        # self.update_movies()
        self.notion.update_movie("/home/cola/Videos/Movies", "12 Years A Slave (2013)")
