"""
FBS logging utilities
"""

# imports
import logging
from pathlib import Path


# path constants
SOURCE_PATH = Path(__file__).parent
PROJECT_PATH = SOURCE_PATH.parent
LOG_PATH = PROJECT_PATH / "logs"
LOG_PATH.mkdir(exist_ok=True, parents=True)
LOG_FILE_PATH = LOG_PATH / "fbs.log"


# logger
def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Returns a logger with the given name and level.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler = logging.FileHandler(LOG_FILE_PATH)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


# default logger
LOGGER = get_logger("fbs")
