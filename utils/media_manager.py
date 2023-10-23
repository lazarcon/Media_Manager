import os
import logging

from pprint import pprint

from .movies import MovieManager

logger = logging.getLogger(__name__)


class MediaManager:

    def __init__(self, config):
        self.movies_manager = MovieManager(
            api_key = config["notion_api_key"],
            movie_database_id=config["notion_media"]["movies"]["movie_db"],
            genre_database_id=config["notion_media"]["movies"]["genre_db"],
            omdb_api_key=config["omdb_api_key"]
        )
        self.local_media_locations = config["local_media"]

    def update(self) -> None:
        self.movies_manager.update(self.local_media_locations)
