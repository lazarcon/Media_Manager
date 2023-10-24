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
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Run in debug mode")
    parser.add_argument("-i", "--info", action="store_true",
                        help="Run in info mode")
    args = parser.parse_args(arguments)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.info:
        logging.basicConfig(level=logging.INFO)

    config = load_config()
    app = MediaManager(config)
    app.run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
