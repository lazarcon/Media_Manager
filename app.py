import sys
import argparse
import logging

from pprint import pprint

from utils.file import load_config
from utils.genres import update_genres
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
                        help="Run all movie manager tasks",
                        type=str.lower, nargs="?", const="all")
    # (1/4) Add more media handling options here to come
    parser.add_argument("-u", "--update", action="store_true",
                        help="Update whishlists")
    parser.add_argument("-g", "--genres", action="store_true",
                        help="Update local genres")
    parser.add_argument("-b", "--backup", action="store_true",
                        help="Create backups if necessary")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Run in debug mode")
    parser.add_argument("-i", "--info", action="store_true",
                        help="Run in info mode")
    args = parser.parse_args(arguments)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.info:
        logging.basicConfig(level=logging.INFO)

    if args.genres:
        update_genres(config)

    app = MediaManager(config)

    if args.update:
        app.update()

    if args.movies:
        if "all" in args.movies:
            locations = movie_locations
        else:
            locations = [movie_location for movie_location in movie_locations if movie_location["label"].lower() in args.movies]
        app.run(movie_locations=locations)
    # (2/4) and add more actual media handling here

    if args.backup:
        movie_backup_location = [movie_location for movie_location in movie_locations if movie_location["label"].lower() == "backup"][0]
        # (3/4) add more backup locations here
        app.backup(movie_backup_location=movie_backup_location)

    if (
        not args.genres
        and not args.movies
        # (4/4) and more missing media handling arguments here
    ):
        # if nothing is to be done, everything is to be done
        # app.run(movie_locations=movie_locations)
        print("Nothing to do.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
