import logging

from typing import Dict

from .models import MovieGenre
from .database import get_session
from .notion import Notion


logger = logging.getLogger(__name__)

def update_movie_genres(config) -> None:
    notion = Notion(api_key=config["notion_api_key"])
    genre_database_id = config["notion_media"]["movies"]["genre_db"]
    notion_genres = notion.load_records(genre_database_id)
    genres_lookup = {}

    for notion_genre in notion_genres:
        for synonym in notion_genre["properties"]["Synonyms"]["multi_select"]:
            genres_lookup[synonym["name"]] = notion_genre["id"]

    session = get_session()
    with session.begin() as transaction:
        local_movie_genres = session.query(MovieGenre).all()
        for movie_genre in local_movie_genres:
            if movie_genre.notion_id is None:
                if movie_genre.genre_name in genres_lookup:
                    movie_genre.notion_id = genres_lookup[movie_genre.genre_name]
                    session.add(movie_genre)
        transaction.commit()


def update_genres(config: Dict) -> None:
    """
    Updates all genres
    """
    update_movie_genres(config)
