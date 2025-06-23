import logging
import sys
from dotenv import load_dotenv
from os import getenv

load_dotenv()
LOG_LEVEL = getenv("LOG_LEVEL", "INFO")

logging_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

logging_handler = logging.StreamHandler(sys.stdout)
logging_handler.setFormatter(logging_formatter)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with a given name.

    Args:
        name (str): Logger name.

    Returns:
        logging.Logger: logging.Logger object.
    """

    logger: logging.Logger = logging.getLogger(name)
    logger.addHandler(logging_handler)
    logger.setLevel(LOG_LEVEL.upper())

    return logger