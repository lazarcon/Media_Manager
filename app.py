import sys
import argparse
import logging

from pprint import pprint

from utils.file import load_config
from utils.media_manager import MediaManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.NOTSET)


def main(arguments):
    """
    Main function for the economy CLI.

    Args:
        arguments (list): Command-line arguments passed to the script.
    """

    config = load_config()
    local_media_locations = config["local_media_locations"]
    movie_locations = local_media_locations["movies"]
    movie_location_choices = [location["label"].lower() for location in movie_locations] + ["all"]

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-m", "--movies",
                        choices=movie_location_choices,
                        type=str.lower, nargs="?", const="all")
    # (1/3) Add more media handling options here to come
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Run in debug mode")
    parser.add_argument("-i", "--info", action="store_true",
                        help="Run in info mode")
    args = parser.parse_args(arguments)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.info:
        logging.basicConfig(level=logging.INFO)

    app = MediaManager(config)
    if (
        not args.movies
        # (2/3) and more missing media handling arguments here
    ):
        app.run(movie_locations=movie_locations)
    else:
        if args.movies:
            if "all" in args.movies:
                locations = movie_locations
            else:
                locations = [movie_location for movie_location in movie_locations if movie_location["label"].lower() in args.movies]
            app.run(movie_locations=locations)
        # (3/3) and add more actual media handling here


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
