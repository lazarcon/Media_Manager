import os
import sys
import time
import logging
import requests

import pandas as pd

from random import randint
from bs4 import BeautifulSoup as bs
from typing import Dict

from .file import load_json, save_json, get_file_age_in_days

logger = logging.getLogger(__name__)

MOVIE_CACHE = "imdb_top_250_movies.json"
FILE_AGE_TRESHOLD = 90


class ImdbRepository:

    def __init__(self):
        self.ranking = {}

    def _fetch_imdb_top_250(self) -> Dict:
        result = {}

        # For monitoring request frequency
        startTime = time.time()
        reqNum = 0

        logger.info("Fetching Webpages...")
        rank = 0
        for i in range(1, 201 + 1, 50):
        #for i in range(1, 50 + 1, 50):
            url = ('https://www.imdb.com/search/title/?groups=top_250&sort=user_rating,desc&start=' \
                + str(i) + '&ref_=adv_nxt')

            # Make a get request
            try:
                response = requests.get(url, headers = {"Accept-Language": "en-US, \
                    en;q=0.5"})
                response.raise_for_status()
            # Throw warning in case of errors
            except requests.exceptions.RequestException as e:
                logger.error(f'\nThere was a problem:\n{e}')
                sys.exit()

            # Pause the loop
            time.sleep(randint(1,4))

            # Monitor the request frequency
            reqNum += 1
            elapsedTime = time.time() - startTime
            logger.debug(f"Request: {reqNum}; Frequency: {reqNum/elapsedTime:.6f} requests/s")

            # Parse the HTML Contents
            imdbSoup = bs(response.text, 'lxml')
            movieContainers = imdbSoup.find_all('div', \
                class_ = 'lister-item mode-advanced')

            for container in movieContainers:
                rank += 1

                # Movie Id
                id = container.img['data-tconst']

                # Movie Name
                title = container.h3.a.text

                # Release Year
                year = container.h3.find('span', class_ = 'lister-item-year').text

                # Movie Genre
                genre = container.p.find('span', class_ = 'genre') \
                    .text.strip('\n').strip()

                # IMDB Rating
                rating = container.strong.text

                # Create to Dict:
                movie = {
                    "rank": rank,
                    "title": title,
                    "year": year,
                    "genre": genre,
                    "rating": rating
                }

                result[id] = movie
        return result

    def _load_ranking(self):
        if (not os.path.exists(MOVIE_CACHE)
            or get_file_age_in_days(MOVIE_CACHE) > FILE_AGE_TRESHOLD
        ):
            data = self._fetch_imdb_top_250()
            save_json(MOVIE_CACHE, data)
        else:
            data = load_json(MOVIE_CACHE)
        return data

    def get_rank(self, imdb_id) -> int:
        if len(self.ranking) == 0:
            self.ranking = self._load_ranking()
        if imdb_id in list(self.ranking.keys()):
            return self.ranking[imdb_id]['rank']
