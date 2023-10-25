import logging

from typing import List, Dict
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

    def run(self, movie_locations: List[Dict] = []) -> None:
        self.movies_manager.run(movie_locations)
