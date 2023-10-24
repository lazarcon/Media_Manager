import os
import logging

import xml.etree.ElementTree as ET

from typing import List

logger = logging.getLogger(__name__)

MAX_ACTORS = 3


class NFO:

    @staticmethod
    def is_nfo_file(filepath: str) -> bool:
        """
        Checks if a file is a .nfo file. Returns True if so.
        """
        return filepath.endswith(".nfo")

    @staticmethod
    def rename_nfo_file(filepath: str) -> str:
        """
        Rename an .nfo file to 'movie.nfo' if it's not already named as such.

        :param filepath: The path to the .nfo file.

        Returns:
            (str): The renamed filepath, or the original filepath if not renamed.
        """
        if not filepath.endswith(".nfo"):
            logger.warning(f"{filepath} is not a .nfo file. It will not be renamed.")
            return filepath

        if filepath.endswith("movie.nfo"):
            # The file is already named 'movie.nfo', nothing to do
            return filepath

        try:
            head, _ = os.path.split(filepath)
            nfo_file = os.path.join(head, "movie.nfo")
            os.rename(filepath, nfo_file)
            logger.info(f"Renamed {filepath} to movie.nfo")
            return nfo_file
        except Exception as e:
            logger.error(f"Error renaming {filepath} to movie.nfo: {str(e)}")
            return filepath

    def __init__(self, filepath: str):
        try:
            tree = ET.parse(filepath)
            self.root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Error parsing XML: {str(e)}")
            self.root = None

    @property
    def title(self) -> str:
        title = self.root.find(".//title")
        if title is not None:
            return title.text

    @property
    def original_title(self) -> str:
        original_title = self.root.find(".//originaltitle")
        if original_title is not None:
            return original_title.text

    @property
    def year(self) -> int:
        year = self.root.find(".//year")
        if year is not None:
            return int(year.text)

    @property
    def duration(self) -> int:
        duration = self.root.find(".//fileinfo/streamdetails/video/durationinseconds")
        if duration is not None:
            return int(duration.text)

    @property
    def tagline_text(self) -> str:
        tagline_text = self.root.find(".//tagline")
        if tagline_text is not None:
            return tagline_text.text

    @property
    def imdb_id(self) -> str:
        imdb_id = self.root.find(".//id")
        if imdb_id is not None:
            imdb_id.text

    @property
    def rating(self) -> float:
        rating = self.root.find(".//rating")
        if rating is not None:
            try:
                return float(rating.text)
            except BaseException:
                # rating could not be converted, so just ignore this
                pass

    @property
    def stars(self) -> str:
        rating = self.rating
        if rating:
            stars = round(rating / 2, 0)
            return "\u2605" * stars

    @property
    def genres(self) -> List[str]:
        genres = []
        for genre in self.root.findall(".//genre"):
            genre = genre.text
            genres.append(genre)
        return genres

    @property
    def actors(self) -> List[str]:
        actors = []
        for actor in self.root.findall(".//actor"):
            name = actor.find("name")
            if name is not None:
                actors.append(name.text)
            if len(actors) >= MAX_ACTORS:
                break
        return actors

    @property
    def directors(self) -> List[str]:
        directors = []
        for director in self.root.findall(".//director"):
            directors.append(director.text)
        return directors

    @property
    def countries(self) -> List[str]:
        countries = []
        for country in self.root.findall(".//country"):
            countries.append(country.text)
        return countries

    @property
    def languages(self) -> List[str]:
        languages = []
        for audio_element in self.root.findall(".//fileinfo/streamdetails/audio"):
            language_element = audio_element.find("language")
            if language_element is not None:
                languages.append(language_element.text)
        return languages

    def is_valid(self):
        return self.title is not None

    def __repr__(self):
        year = "None" if self.year is None else self.year
        return f"{self.title} ({year})"
