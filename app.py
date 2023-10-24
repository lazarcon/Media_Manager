import sys
import argparse
import logging

from pprint import pprint

from utils.file import load_config
from utils.media_manager import MediaManager
from utils.database import create_tables

logger = logging.getLogger(__name__)
logger.setLevel(logging.NOTSET)


def setup(config):
    create_tables()


def main(arguments):
    """
    Main function for the economy CLI.

    Args:
        arguments (list): Command-line arguments passed to the script.
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-s", "--setup", action="store_true",
                        help="Creates all necessary tables")
    parser.add_argument("-u", "--update", action="store_true",
                        help="Update Notion Database from local storage")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Run in debug mode")
    parser.add_argument("-i", "--info", action="store_true",
                        help="Run in info mode")
    args = parser.parse_args(arguments)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    if args.info:
        logging.basicConfig(level=logging.INFO)

    config = load_config()

    if args.setup:
        setup(config)

    if args.update:
        app = MediaManager(config)
        app.update()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))



