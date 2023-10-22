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
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-u", "--update", action="store_true",
                        help="Update Notion Database from local storage")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Run in debug mode")
    args = parser.parse_args(arguments)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    config = load_config()
    app = MediaManager(config)
    if args.update:
        app.update()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))



