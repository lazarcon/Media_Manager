import os
import sys
import time
import logging
import requests
import re

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
        self.rankings = {}

    def _find_first_blank(self, title_str: str) -> int:
        for index in range(0, len(title_str)):
            if title_str[index] == " ":
                return index
        return None


    def _fetch_imdb_top_250(self) -> Dict:
        # driver = Chrome(service=Service(ChromeDriverManager().install()))
        url = "https://www.imdb.com/chart/top/"
        try:
            # self.driver.get(url)
            response = requests.get(url, headers = {"Accept-Language": "en-US, \
                en;q=0.5, ", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36"})
            response.raise_for_status()
            #response = self.driver.page_source
        # Throw warning in case of errors
        except requests.exceptions.RequestException as e:
            logger.error(f'\nThere was a problem:\n{e}')
            sys.exit()

        imdbSoup = bs(response.text, 'lxml')
        movieContainers = imdbSoup.find_all('li', \
                class_ = 'ipc-metadata-list-summary-item')
        result = {}
        id_pattern = r"/title/(tt\d{7})/?.*"
        title_pattern = r"(\d+)\.\s+(.+)"
        for container in movieContainers:
            links = container.find_all('a')
            title_link = links[-1]
            href = title_link["href"]
            href_match = re.search(id_pattern, href)
            id = href_match.group(1)
            title_str = title_link.text
            title_match = re.search(title_pattern, title_str)
            rank = title_match.group(1)
            title = title_match.group(2)

            spans = container.find_all("span", class_ = "cli-title-metadata-item")
            year = int(spans[0].text)
            ratings_container = container.find("div", class_ = "cli-ratings-container")
            ratings_span = ratings_container.find("span")
            rating = float(ratings_span["aria-label"][-3:])
            # Create to Dict:
            movie = {
                "rank": rank,
                "title": title,
                "year": year,
                "rating": rating
            }
            result[id] = movie
        return result

    def is_update_due(self) -> bool:
        return (not os.path.exists(MOVIE_CACHE)
            or get_file_age_in_days(MOVIE_CACHE) > FILE_AGE_TRESHOLD
        )

    def _load_ranking(self):
        if self.is_update_due():
            data = self._fetch_imdb_top_250()
            save_json(MOVIE_CACHE, data)
        else:
            data = load_json(MOVIE_CACHE)
        return data

    def get_rank(self, imdb_id) -> int:
        if len(self.rankings) == 0:
            self.rankings = self._load_ranking()
        if imdb_id in list(self.rankings.keys()):
            return self.rankings[imdb_id]['rank']

    def get_rankings(self) -> dict:
        if len(self.rankings) == 0:
            self.rankings = self._load_ranking()
        return self.rankings
